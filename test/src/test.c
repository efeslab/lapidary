/**
 * Test program for Lapidary simulations.
 * 
 * Before you come yelling at me, yes, I know, this is not the best way to 
 * compute the fibonacci sequence. I just wanted a simple program that took
 * several seconds to finish running so that realistic checkpoints could be
 * created from it.
 */
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>

uint64_t fib(uint64_t i) {
    if (i <= 1) {
        return i;
    }

    return fib(i - 1) + fib(i - 2);
}

int main(int argc, char **argv) {
    for (uint64_t i = 0; i < 50; ++i) {
        printf("fib(%lu) = %lu\n", i, fib(i));
    }

    return 0;
}
