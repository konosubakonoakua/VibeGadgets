#include "fifo.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Helpers */
static void collect_sum(const void *el, void *sum) {
  *(int32_t *)sum += *(const int32_t *)el;
}
static void foreach_check(const void *el) { /* No-op, could be extended */ }
static bool is_even(const void *el) { return (*(const int32_t *)el % 2) == 0; }

int main(void) {
  /* ---------- Static FIFO ---------- */
  int32_t buffer[8];
  fifo_t f_static;
  assert(fifo_init(&f_static, buffer, 8, sizeof(int32_t)));

  /* Push values 1..5 */
  for (int i = 1; i <= 5; i++)
    assert(fifo_push(&f_static, &i));
  assert(fifo_count(&f_static) == 5);
  assert(!fifo_is_empty(&f_static));
  assert(!fifo_is_full(&f_static));

  /* Peek */
  assert(*(int32_t *)fifo_peek_first(&f_static) == 1);
  assert(*(int32_t *)fifo_peek_last(&f_static) == 5);

  /* Pop */
  int32_t val;
  assert(fifo_pop(&f_static, &val) && val == 1);
  assert(fifo_count(&f_static) == 4);

  /* foreach (just runs) */
  fifo_foreach(&f_static, foreach_check);

  /* find even */
  const int32_t *found = fifo_find(&f_static, is_even);
  assert(found && *found == 2);

  /* sum */
  int32_t sum = 0;
  fifo_sum(&f_static, &sum, add_int32);
  assert(sum == (2 + 3 + 4 + 5));

  /* copy range */
  int32_t dst[4] = {0};
  uint32_t copied = fifo_copy_range(&f_static, 0, 4, dst);
  assert(copied == 4);
  assert(memcmp(dst, (int32_t[]){2, 3, 4, 5}, 4 * sizeof(int32_t)) == 0);

  /* clear */
  fifo_clear(&f_static);
  assert(fifo_is_empty(&f_static));

  /* ---------- Dynamic FIFO ---------- */
  fifo_t *f_dyn = fifo_create(16, sizeof(int32_t));
  assert(f_dyn);

  for (int i = 10; i < 20; i++)
    assert(fifo_push(f_dyn, &i));
  assert(fifo_count(f_dyn) == 10);

  /* sum_parallel */
  int32_t sum_dyn = 0;
  fifo_sum_parallel(f_dyn, &sum_dyn, add_int32);
  int expected = 0;
  for (int i = 10; i < 20; i++)
    expected += i;
  assert(sum_dyn == expected);

  fifo_destroy(f_dyn);

  printf("All FIFO tests passed\n");
  return 0;
}
