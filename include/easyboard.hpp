#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <filesystem>
#include <chrono>
#include <mutex>
#include <iomanip>
#include <sstream>

namespace easyboard {

class SummaryWriter {
public:
    /**
     * @brief Initializes the SummaryWriter.
     * @param log_dir Absolute or relative path for storage.
     * @param tags List of string tags to identify and group the run.
     * @param flush_size Number of items in buffer before writing to disk.
     * @param flush_secs Time in seconds before forcing a disk write.
     */
    SummaryWriter(const std::string& log_dir = "logs/default_exp",
                  const std::vector<std::string>& tags = {},
                  size_t flush_size = 1000,
                  double flush_secs = 2.0)
        : log_dir_(log_dir),
          tags_(tags),
          flush_size_(flush_size),
          flush_secs_(flush_secs),
          closed_(false) 
    {
        namespace fs = std::filesystem;

        // Create directories
        fs::create_directories(log_dir_);

        // Generate timestamped metric file
        std::string timestamp_str = get_datetime_str();
        csv_path_ = log_dir_ / ("metrics_" + timestamp_str + ".csv");
        config_path_ = log_dir_ / "config.json";
        meta_path_ = log_dir_ / "run_meta.json";

        last_flush_time_ = get_time_secs();

        save_metadata();
        initialize_csv();
    }

    // Disable copy and move semantics to prevent file handle / mutex issues
    SummaryWriter(const SummaryWriter&) = delete;
    SummaryWriter& operator=(const SummaryWriter&) = delete;

    /**
     * @brief Destructor acts as __exit__ and atexit.register
     */
    ~SummaryWriter() {
        close();
    }

    /**
     * @brief Adds/updates config. Merges with in-memory configs and overwrites the JSON file.
     */
    void add_config(const std::map<std::string, std::string>& config_dict) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& [k, v] : config_dict) {
            config_cache_[k] = v;
        }
        write_config_json();
    }

    void add_scalar(const std::string& metric_name, double value, int step) {
        std::lock_guard<std::mutex> lock(mutex_);
        buffer_.push_back({get_time_secs(), "scalar", metric_name, step, value});
        check_flush();
    }

    void add_summary(const std::string& metric_name, double value) {
        std::lock_guard<std::mutex> lock(mutex_);
        buffer_.push_back({get_time_secs(), "summary", metric_name, -1, value});
        check_flush();
    }

    void flush() {
        std::lock_guard<std::mutex> lock(mutex_);
        flush_impl();
    }

    void close() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (closed_) return;
        flush_impl();
        closed_ = true;
    }

private:
    struct LogEntry {
        double timestamp;
        std::string type;
        std::string metric_name;
        int step;
        double value;
    };

    std::filesystem::path log_dir_;
    std::vector<std::string> tags_;
    size_t flush_size_;
    double flush_secs_;

    std::filesystem::path csv_path_;
    std::filesystem::path config_path_;
    std::filesystem::path meta_path_;

    std::vector<LogEntry> buffer_;
    double last_flush_time_;
    std::mutex mutex_;
    bool closed_;

    // To avoid bringing in heavy JSON libraries (like nlohmann/json) just for merging,
    // we keep the state of the config in memory and overwrite the file.
    std::map<std::string, std::string> config_cache_;

    // --- Helper Methods (must be called with mutex_ locked) ---

    void save_metadata() {
        std::ofstream f(meta_path_);
        if (!f.is_open()) return;
        f << "{\n  \"tags\": [\n";
        for (size_t i = 0; i < tags_.size(); ++i) {
            f << "    \"" << escape_json(tags_[i]) << "\"";
            if (i < tags_.size() - 1) f << ",";
            f << "\n";
        }
        f << "  ]\n}\n";
    }

    void initialize_csv() {
        if (!std::filesystem::exists(csv_path_)) {
            std::ofstream f(csv_path_);
            f << "timestamp,type,metric_name,step,value\n";
        }
    }

    void write_config_json() {
        std::ofstream f(config_path_);
        if (!f.is_open()) return;
        f << "{\n";
        size_t count = 0;
        for (const auto& [k, v] : config_cache_) {
            f << "  \"" << escape_json(k) << "\": \"" << escape_json(v) << "\"";
            if (++count < config_cache_.size()) f << ",";
            f << "\n";
        }
        f << "}\n";
    }

    void check_flush() {
        if (buffer_.size() >= flush_size_ || 
            (get_time_secs() - last_flush_time_) >= flush_secs_) {
            flush_impl();
        }
    }

    void flush_impl() {
        if (buffer_.empty()) return;

        std::ofstream f(csv_path_, std::ios::app);
        if (f.is_open()) {
            // Set high precision for double values (timestamp and metric values)
            f << std::fixed << std::setprecision(6);
            for (const auto& entry : buffer_) {
                f << entry.timestamp << ","
                  << entry.type << ","
                  << entry.metric_name << ","
                  << entry.step << ","
                  << entry.value << "\n";
            }
        }
        buffer_.clear();
        last_flush_time_ = get_time_secs();
    }

    // --- Utility Methods ---

    static double get_time_secs() {
        auto now = std::chrono::system_clock::now();
        return std::chrono::duration<double>(now.time_since_epoch()).count();
    }

    static std::string get_datetime_str() {
        auto now = std::chrono::system_clock::now();
        std::time_t now_c = std::chrono::system_clock::to_time_t(now);
        std::tm* now_tm = std::localtime(&now_c);
        
        std::ostringstream ss;
        ss << std::put_time(now_tm, "%Y%m%d_%H%M%S");
        return ss.str();
    }

    // Simple JSON escape to keep output valid
    static std::string escape_json(const std::string& s) {
        std::ostringstream o;
        for (auto c = s.cbegin(); c != s.cend(); c++) {
            if (*c == '"' || *c == '\\' || ('\x00' <= *c && *c <= '\x1f')) {
                o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (int)*c;
            } else {
                o << *c;
            }
        }
        return o.str();
    }
};

} // namespace easyboard