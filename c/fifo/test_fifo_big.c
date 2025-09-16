#include "fifo.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
/* #include <string.h> */

/* Simple predicate and foreach helpers */
static void foreach_noop(const void *el) { (void)el; }
static bool is_div_1000(const void *el) {
  return (*(const int32_t *)el % 1000) == 0;
}

int main(void) {
  const uint32_t CAP = 10001; /* capacity (1 slot unused, usable = 10000) */
  const uint32_t N = 10000;   /* number of elements to push */
  fifo_t *f = fifo_create(CAP, sizeof(int32_t));
  assert(f);

  /* Push 10,000 ints */
  for (int32_t i = 1; i <= (int32_t)N; i++) {
    assert(fifo_push(f, &i));
  }
  assert(fifo_count(f) == N);
  assert(fifo_is_full(f));

  /* Peek first/last */
  assert(*(int32_t *)fifo_peek_first(f) == 1);
  assert(*(int32_t *)fifo_peek_last(f) == (int32_t)N);

  /* Sum check (formula for 1+2+..+N = N*(N+1)/2) */
  int64_t sum = 0;
  fifo_sum_parallel(f, &sum, add_int32_to_int64);
  int64_t expected = ((int64_t)N * (N + 1)) / 2;
  assert(sum == expected);

  /* Find element divisible by 1000 */
  const int32_t *found = fifo_find(f, is_div_1000);
  assert(found && *found == 1000);

  /* foreach sanity check */
  fifo_foreach(f, foreach_noop);

  /* Copy all and check last 5 */
  int32_t *dst = malloc(N * sizeof(int32_t));
  assert(dst);
  uint32_t copied = fifo_copy_all(f, dst);
  assert(copied == N);
  for (int i = N - 5; i < (int)N; i++) {
    assert(dst[i] == i + 1);
  }
  free(dst);

  /* Pop half */
  for (int i = 0; i < (int)N / 2; i++) {
    int32_t val;
    assert(fifo_pop(f, &val));
    assert(val == i + 1);
  }
  assert(fifo_count(f) == N / 2);

  /* Push again to wrap around */
  for (int i = 0; i < (int)N / 2; i++) {
    int32_t val = 100000 + i;
    assert(fifo_push(f, &val));
  }
  assert(fifo_count(f) == N);

  /* Check wrap-around correctness */
  assert(*(int32_t *)fifo_peek_first(f) == N / 2 + 1);
  assert(*(int32_t *)fifo_peek_last(f) == 100000 + N / 2 - 1);

  fifo_destroy(f);
  printf("Big FIFO test (%u elements) passed!\n", N);
  return 0;
}
