#ifndef FIFO_H
#define FIFO_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>
#include <stdint.h>

#ifdef FIFO_THREADSAFE
#include <pthread.h>
#endif

/**
 * @file fifo.h
 * @brief Generic FIFO (First-In-First-Out) circular buffer
 */

typedef struct fifo {
  void *buffer;       /**< Data buffer */
  uint32_t size;      /**< Capacity in elements (including 1 reserved slot) */
  uint32_t elem_size; /**< Size of each element in bytes */
  uint32_t head;      /**< Next write position */
  uint32_t tail;      /**< Oldest element */
  bool dynamic;       /**< Whether buffer was allocated internally */
#ifdef FIFO_THREADSAFE
  pthread_mutex_t lock; /**< Mutex for thread safety */
#endif
} fifo_t;

/* -------- Initialization -------- */
bool fifo_init(fifo_t *f, void *buffer, uint32_t size, uint32_t elem_size);
fifo_t *fifo_create(uint32_t size, uint32_t elem_size);
void fifo_destroy(fifo_t *f);
void fifo_clear(fifo_t *f);

/* -------- Basic Operations -------- */
bool fifo_push(fifo_t *f, const void *data);
bool fifo_pop(fifo_t *f, void *data);

/* -------- Status -------- */
static inline bool fifo_is_empty(const fifo_t *f) {
  return (!f || f->head == f->tail);
}
static inline bool fifo_is_full(const fifo_t *f) {
  return (!f) ? false : ((f->head + 1) % f->size == f->tail);
}
static inline uint32_t fifo_count(const fifo_t *f) {
  return (!f) ? 0 : (f->head + f->size - f->tail) % f->size;
}
static inline uint32_t fifo_capacity(const fifo_t *f) {
  return (!f) ? 0 : (f->size - 1);
}
static inline uint32_t fifo_remaining(const fifo_t *f) {
  return (!f) ? 0 : (fifo_capacity(f) - fifo_count(f));
}

/* -------- Data Access -------- */
const void *fifo_peek_first(const fifo_t *f);
const void *fifo_peek_last(const fifo_t *f);
const void *fifo_get(const fifo_t *f, uint32_t index);

/* -------- Bulk Operations -------- */
uint32_t fifo_copy_all(const fifo_t *f, void *dst);
uint32_t fifo_copy_range(const fifo_t *f, uint32_t start, uint32_t count,
                         void *dst);

/* -------- Functional Ops -------- */
void fifo_foreach(const fifo_t *f, void (*func)(const void *el));
const void *fifo_find(const fifo_t *f, bool (*pred)(const void *el));
void fifo_sum(const fifo_t *f, void *sum,
              void (*add_func)(const void *el, void *sum));
void fifo_sum_parallel(fifo_t *f, void *sum,
                       void (*add_func)(const void *el, void *sum));

/* -------- Built-in Adders -------- */
/* 8-bit */
void add_int8(const void *el, void *sum);
void add_uint8(const void *el, void *sum);
/* 16-bit */
void add_int16(const void *el, void *sum);
void add_uint16(const void *el, void *sum);
/* 32-bit */
void add_int32(const void *el, void *sum);
void add_uint32(const void *el, void *sum);
void add_float(const void *el, void *sum);
/* 64-bit */
void add_int64(const void *el, void *sum);
void add_uint64(const void *el, void *sum);
void add_double(const void *el, void *sum);

/* ---------- Cross-size adders ---------- */
/* 32-bit integers into 64-bit sum */
void add_int32_to_int64(const void *el, void *sum);
void add_uint32_to_uint64(const void *el, void *sum);
/* 32-bit float into double sum */
void add_float_to_double(const void *el, void *sum);
/* Optional: 64-bit integers into double sum */
void add_int64_to_double(const void *el, void *sum);
void add_uint64_to_double(const void *el, void *sum);

#ifdef __cplusplus
}
#endif
#endif /* FIFO_H */
