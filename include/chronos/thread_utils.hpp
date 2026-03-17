#pragma once

#include <iostream>
#include <thread>

#ifdef __linux__
#include <pthread.h>
#include <sched.h>
#elif defined(__APPLE__)
#include <mach/thread_policy.h>
#include <mach/thread_act.h>
#include <mach/mach_init.h>
#endif

namespace chronos {

/**
 * @brief Pin the calling thread to a specific CPU core.
 * @param core_id The index of the core (0-indexed).
 * @return True if successful.
 */
inline bool pinThreadToCore([[maybe_unused]] int core_id) {
#ifdef __linux__
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);
    pthread_t current_thread = pthread_self();
    return pthread_setaffinity_np(current_thread, sizeof(cpu_set_t), &cpuset) == 0;
#elif defined(__APPLE__)
    // Darwin uses "thread affinity tags" instead of hard pinning to a core ID.
    // Threads with the same tag will be scheduled on the same L2 cache if possible.
    thread_affinity_policy_data_t policy = { core_id };
    return thread_policy_set(mach_thread_self(), THREAD_AFFINITY_POLICY, 
                             (thread_policy_t)&policy, THREAD_AFFINITY_POLICY_COUNT) == KERN_SUCCESS;
#else
    return false;
#endif
}

/**
 * @brief Set the current thread to a high priority.
 */
inline void setMaxPriority() {
#ifdef __linux__
    struct sched_param param;
    param.sched_priority = sched_get_priority_max(SCHED_FIFO);
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);
#endif
}

} // namespace chronos
