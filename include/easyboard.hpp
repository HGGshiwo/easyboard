#pragma once

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <chrono>
#include <mutex>
#include <iomanip>
#include <sstream>
#include <ctime>

// --- 跨平台目录创建支持 (替代 C++17 std::filesystem) ---
#ifdef _WIN32
    #include <direct.h>
    #define MKDIR_SINGLE(path) _mkdir((path).c_str())
#else
    #include <sys/stat.h>
    #define MKDIR_SINGLE(path) mkdir((path).c_str(), 0777)
#endif

namespace easyboard {

class SummaryWriter {
public:
    SummaryWriter(const std::string& log_dir = "logs/default_exp",
                  const std::vector<std::string>& tags = std::vector<std::string>(),
                  size_t flush_size = 1000,
                  double flush_secs = 2.0)
        : log_dir_(log_dir),
          tags_(tags),
          flush_size_(flush_size),
          flush_secs_(flush_secs),
          closed_(false) 
    {
        // 递归创建目录
        makedirs(log_dir_);

        // 生成时间戳文件名
        std::string timestamp_str = get_datetime_str();
        csv_path_ = log_dir_ + "/metrics_" + timestamp_str + ".csv";
        config_path_ = log_dir_ + "/config.json";
        meta_path_ = log_dir_ + "/run_meta.json";

        last_flush_time_ = get_time_secs();

        save_metadata();
        initialize_csv();
    }

    // 禁用拷贝和移动
    SummaryWriter(const SummaryWriter&) = delete;
    SummaryWriter& operator=(const SummaryWriter&) = delete;

    ~SummaryWriter() {
        close();
    }

    void add_config(const std::map<std::string, std::string>& config_dict) {
        std::lock_guard<std::mutex> lock(mutex_);
        // C++14: 使用传统的迭代器/范围for循环，无结构化绑定
        for (const auto& kv : config_dict) {
            config_cache_[kv.first] = kv.second;
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

    std::string log_dir_;
    std::vector<std::string> tags_;
    size_t flush_size_;
    double flush_secs_;

    std::string csv_path_;
    std::string config_path_;
    std::string meta_path_;

    std::vector<LogEntry> buffer_;
    double last_flush_time_;
    std::mutex mutex_;
    bool closed_;

    std::map<std::string, std::string> config_cache_;

    // --- Helper Methods ---

    static void makedirs(const std::string& path) {
        std::string current_path;
        for (char c : path) {
            if (c == '/' || c == '\\') {
                if (!current_path.empty()) {
                    MKDIR_SINGLE(current_path); // 忽略返回值，如果目录已存在则继续
                }
            }
            current_path += c;
        }
        if (!current_path.empty()) {
            MKDIR_SINGLE(current_path);
        }
    }

    static bool file_exists(const std::string& path) {
        std::ifstream f(path.c_str());
        return f.good();
    }

    void save_metadata() {
        std::ofstream f(meta_path_.c_str());
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
        if (!file_exists(csv_path_)) {
            std::ofstream f(csv_path_.c_str());
            f << "timestamp,type,metric_name,step,value\n";
        }
    }

    void write_config_json() {
        std::ofstream f(config_path_.c_str());
        if (!f.is_open()) return;
        f << "{\n";
        size_t count = 0;
        // C++14: 使用 kv.first 和 kv.second
        for (const auto& kv : config_cache_) {
            f << "  \"" << escape_json(kv.first) << "\": \"" << escape_json(kv.second) << "\"";
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

        std::ofstream f(csv_path_.c_str(), std::ios::app);
        if (f.is_open()) {
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

    static std::string escape_json(const std::string& s) {
        std::ostringstream o;
        for (auto c = s.cbegin(); c != s.cend(); ++c) {
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