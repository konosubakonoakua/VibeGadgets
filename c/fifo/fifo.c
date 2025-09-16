#include "fifo.h"
#include <stdlib.h>
#include <string.h>

/* Internal macros for locking */
#ifdef FIFO_THREADSAFE
#define FIFO_LOCK(f) pthread_mutex_lock(&(f)->lock)
#define FIFO_UNLOCK(f) pthread_mutex_unlock(&(f)->lock)
#else
#define FIFO_LOCK(f)
#define FIFO_UNLOCK(f)
#endif

/* ---------- Initialization ---------- */
bool fifo_init(fifo_t *f, void *buffer, uint32_t size, uint32_t elem_size) {
  if (!f || !buffer || size < 2 || elem_size == 0)
    return false;
  f->buffer = buffer;
  f->size = size;
  f->elem_size = elem_size;
  f->head = 0;
  f->tail = 0;
  f->dynamic = false;
#ifdef FIFO_THREADSAFE
  pthread_mutex_init(&f->lock, NULL);
#endif
  return true;
}

fifo_t *fifo_create(uint32_t size, uint32_t elem_size) {
  if (size < 2 || elem_size == 0)
    return NULL;

  fifo_t *f = (fifo_t *)malloc(sizeof(fifo_t));
  if (!f)
    return NULL;

  void *buf = malloc(size * elem_size);
  if (!buf) {
    free(f);
    return NULL;
  }

  fifo_init(f, buf, size, elem_size);
  f->dynamic = true;
  return f;
}

void fifo_destroy(fifo_t *f) {
  if (!f)
    return;
#ifdef FIFO_THREADSAFE
  pthread_mutex_destroy(&f->lock);
#endif
  if (f->dynamic && f->buffer) {
    free(f->buffer);
    f->buffer = NULL;
  }
  free(f);
}

void fifo_clear(fifo_t *f) {
  if (f) {
    FIFO_LOCK(f);
    f->head = f->tail = 0;
    FIFO_UNLOCK(f);
  }
}

/* ---------- Basic operations ---------- */
bool fifo_push(fifo_t *f, const void *data) {
  if (!f || !data)
    return false;
  FIFO_LOCK(f);
  if (fifo_is_full(f)) {
    FIFO_UNLOCK(f);
    return false;
  }

  void *dest = (char *)f->buffer + (f->head * f->elem_size);
  memcpy(dest, data, f->elem_size);

  f->head = (f->head + 1) % f->size;
  FIFO_UNLOCK(f);
  return true;
}

bool fifo_pop(fifo_t *f, void *data) {
  if (!f)
    return false;
  FIFO_LOCK(f);
  if (fifo_is_empty(f)) {
    FIFO_UNLOCK(f);
    return false;
  }

  void *src = (char *)f->buffer + (f->tail * f->elem_size);
  if (data)
    memcpy(data, src, f->elem_size);

  f->tail = (f->tail + 1) % f->size;
  FIFO_UNLOCK(f);
  return true;
}

/* ---------- Data access ---------- */
const void *fifo_peek_first(const fifo_t *f) {
  if (!f)
    return NULL;
  FIFO_LOCK((fifo_t *)f);
  const void *ptr = fifo_is_empty(f)
                        ? NULL
                        : (const char *)f->buffer + f->tail * f->elem_size;
  FIFO_UNLOCK((fifo_t *)f);
  return ptr;
}

const void *fifo_peek_last(const fifo_t *f) {
  if (!f)
    return NULL;
  FIFO_LOCK((fifo_t *)f);
  const void *ptr = NULL;
  if (!fifo_is_empty(f)) {
    uint32_t idx = (f->head == 0) ? (f->size - 1) : (f->head - 1);
    ptr = (const char *)f->buffer + idx * f->elem_size;
  }
  FIFO_UNLOCK((fifo_t *)f);
  return ptr;
}

const void *fifo_get(const fifo_t *f, uint32_t index) {
  if (!f)
    return NULL;
  FIFO_LOCK((fifo_t *)f);
  uint32_t cnt = fifo_count(f);
  const void *ptr = NULL;
  if (index < cnt) {
    uint32_t idx = (f->tail + index) % f->size;
    ptr = (const char *)f->buffer + idx * f->elem_size;
  }
  FIFO_UNLOCK((fifo_t *)f);
  return ptr;
}

/* ---------- Bulk operations ---------- */
uint32_t fifo_copy_all(const fifo_t *f, void *dst) {
  if (!f || !dst)
    return 0;
  return fifo_copy_range(f, 0, fifo_count(f), dst);
}

uint32_t fifo_copy_range(const fifo_t *f, uint32_t start, uint32_t count,
                         void *dst) {
  if (!f || !dst)
    return 0;
  FIFO_LOCK((fifo_t *)f);
  uint32_t avail = fifo_count(f);
  if (start >= avail) {
    FIFO_UNLOCK((fifo_t *)f);
    return 0;
  }
  if (start + count > avail)
    count = avail - start;

  uint32_t start_idx = (f->tail + start) % f->size;
  if (start_idx + count <= f->size) {
    memcpy(dst, (char *)f->buffer + start_idx * f->elem_size,
           count * f->elem_size);
  } else {
    uint32_t first_part = f->size - start_idx;
    uint32_t bytes_first = first_part * f->elem_size;
    uint32_t bytes_second = (count - first_part) * f->elem_size;
    memcpy(dst, (char *)f->buffer + start_idx * f->elem_size, bytes_first);
    memcpy((char *)dst + bytes_first, f->buffer, bytes_second);
  }
  FIFO_UNLOCK((fifo_t *)f);
  return count;
}

/* ---------- Functional operations ---------- */
void fifo_foreach(const fifo_t *f, void (*func)(const void *el)) {
  if (!f || !func)
    return;
  FIFO_LOCK((fifo_t *)f);
  uint32_t n = fifo_count(f);
  for (uint32_t i = 0; i < n; i++) {
    uint32_t idx = (f->tail + i) % f->size;
    const void *el = (const char *)f->buffer + idx * f->elem_size;
    func(el);
  }
  FIFO_UNLOCK((fifo_t *)f);
}

const void *fifo_find(const fifo_t *f, bool (*pred)(const void *el)) {
  if (!f || !pred)
    return NULL;
  FIFO_LOCK((fifo_t *)f);
  uint32_t n = fifo_count(f);
  const void *result = NULL;
  for (uint32_t i = 0; i < n; i++) {
    uint32_t idx = (f->tail + i) % f->size;
    const void *el = (const char *)f->buffer + idx * f->elem_size;
    if (pred(el)) {
      result = el;
      break;
    }
  }
  FIFO_UNLOCK((fifo_t *)f);
  return result;
}

void fifo_sum(const fifo_t *f, void *sum,
              void (*add_func)(const void *el, void *sum)) {
  if (!f || !sum || !add_func)
    return;
  FIFO_LOCK((fifo_t *)f);
  uint32_t n = fifo_count(f);
  for (uint32_t i = 0; i < n; i++) {
    uint32_t idx = (f->tail + i) % f->size;
    const void *el = (const char *)f->buffer + idx * f->elem_size;
    add_func(el, sum);
  }
  FIFO_UNLOCK((fifo_t *)f);
}

/* Thread-safe summation */
void fifo_sum_parallel(fifo_t *f, void *sum,
                       void (*add_func)(const void *el, void *sum)) {
  fifo_sum(f, sum, add_func);
}

/* ---------- Built-in adders ---------- */
void add_int8(const void *el, void *sum) {
  *(int8_t *)sum += *(const int8_t *)el;
}
void add_uint8(const void *el, void *sum) {
  *(uint8_t *)sum += *(const uint8_t *)el;
}
void add_int16(const void *el, void *sum) {
  *(int16_t *)sum += *(const int16_t *)el;
}
void add_uint16(const void *el, void *sum) {
  *(uint16_t *)sum += *(const uint16_t *)el;
}
void add_int32(const void *el, void *sum) {
  *(int32_t *)sum += *(const int32_t *)el;
}
void add_uint32(const void *el, void *sum) {
  *(uint32_t *)sum += *(const uint32_t *)el;
}
void add_int64(const void *el, void *sum) {
  *(int64_t *)sum += *(const int64_t *)el;
}
void add_uint64(const void *el, void *sum) {
  *(uint64_t *)sum += *(const uint64_t *)el;
}
void add_float(const void *el, void *sum) {
  *(float *)sum += *(const float *)el;
}
void add_double(const void *el, void *sum) {
  *(double *)sum += *(const double *)el;
}
/* ---------- Cross-size adders ---------- */

/* 32-bit integers into 64-bit sum */
void add_int32_to_int64(const void *el, void *sum) {
  *(int64_t *)sum += (int64_t)*(const int32_t *)el;
}

void add_uint32_to_uint64(const void *el, void *sum) {
  *(uint64_t *)sum += (uint64_t)*(const uint32_t *)el;
}

/* 32-bit float into double sum */
void add_float_to_double(const void *el, void *sum) {
  *(double *)sum += (double)*(const float *)el;
}

/* Optional: 64-bit integers into double sum */
void add_int64_to_double(const void *el, void *sum) {
  *(double *)sum += (double)*(const int64_t *)el;
}

void add_uint64_to_double(const void *el, void *sum) {
  *(double *)sum += (double)*(const uint64_t *)el;
}
