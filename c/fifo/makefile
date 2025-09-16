CC      := gcc
CFLAGS  := -Wall -Wextra -O2 -g
LDFLAGS :=
SRC     := fifo.c
HDR     := fifo.h

# Threadsafe build option
ifdef THREADSAFE
    CFLAGS  += -DFIFO_THREADSAFE
    LDFLAGS += -lpthread
endif

# Test executables
TESTS := test_fifo test_fifo_big

all: $(TESTS)

# Unit test
test_fifo: test_fifo.c $(SRC) $(HDR)
	$(CC) $(CFLAGS) -o $@ test_fifo.c $(SRC) $(LDFLAGS)

# Big stress test
test_fifo_big: test_fifo_big.c $(SRC) $(HDR)
	$(CC) $(CFLAGS) -o $@ test_fifo_big.c $(SRC) $(LDFLAGS)

run: all
	@echo "Running unit tests..."
	./test_fifo
	@echo "Running stress tests..."
	./test_fifo_big

clean:
	rm -f $(TESTS) *.o *.gcda *.gcno *.gcov

help:
	@echo "Available targets:"
	@echo "  make            - Build all tests (default)"
	@echo "  make run        - Build and run all tests"
	@echo "  make clean      - Remove binaries and build artifacts"
	@echo "  make help       - Show this help"
	@echo ""
	@echo "Options:"
	@echo "  THREADSAFE=1    - Enable pthread-based locking in FIFO"
	@echo ""
	@echo "Examples:"
	@echo "  make run                # Build & run without thread safety"
	@echo "  make THREADSAFE=1 run   # Build & run with thread safety"

.PHONY: all run clean help
