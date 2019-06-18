/* Multiple versions of mempcpy.
   All versions must be listed in ifunc-impl-list.c.
   Copyright (C) 2017-2019 Free Software Foundation, Inc.
   This file is part of the GNU C Library.

   The GNU C Library is free software; you can redistribute it and/or
   modify it under the terms of the GNU Lesser General Public
   License as published by the Free Software Foundation; either
   version 2.1 of the License, or (at your option) any later version.

   The GNU C Library is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public
   License along with the GNU C Library; if not, see
   <http://www.gnu.org/licenses/>.  */

/* Define multiple versions only for the definition in libc.  */
#if IS_IN (libc)
# define mempcpy __redirect_mempcpy
# define __mempcpy __redirect___mempcpy
# define NO_MEMPCPY_STPCPY_REDIRECT
# define __NO_STRING_INLINES
# include <string.h>
# undef mempcpy
# undef __mempcpy

extern __typeof (__redirect_mempcpy) __mempcpy_sgx ;

# define SYMBOL_NAME mempcpy
# include "ifunc-memmove.h"

libc_ifunc_redirected (__redirect_mempcpy, __mempcpy, IFUNC_SELECTOR ());

weak_alias (__mempcpy, mempcpy)
# ifdef SHARED
__hidden_ver1 (__mempcpy, __GI___mempcpy, __redirect___mempcpy)
  __attribute__ ((visibility ("hidden"))) __attribute_copy__ (mempcpy);
__hidden_ver1 (mempcpy, __GI_mempcpy, __redirect_mempcpy)
  __attribute__ ((visibility ("hidden"))) __attribute_copy__ (mempcpy);
# endif
#endif


/*
 * sizeof(word) MUST BE A POWER OF TWO
 * SO THAT wmask BELOW IS ALL ONES
 */
typedef long word;      /* "word" used for optimal copy speed */

#define wsize   sizeof(word)
#define wmask   (wsize - 1)

typedef long unsigned int size_t;
#define MEMPCPY
#ifdef MEMPCPY
void *
__mempcpy_sgx(void *dst0, const void *src0, size_t length)
#else
/*
 * Copy a block of memory, handling overlap.
 */
/* void */
/* bcopy(const void *src0, void *dst0, size_t length) */
#endif
{
    char *dst = (char *)dst0;
    const char *src = (const char *)src0;
    size_t t;

#ifdef MEMPCPY
    size_t len = length;
#endif

    if (length == 0 || dst == src)      /* nothing to do */
        goto done;

    /*
     * Macros: loop-t-times; and loop-t-times, t>0
     */
#define TLOOP(s) if (t) TLOOP1(s)
#define TLOOP1(s) do { s; } while (--t)

    if ((unsigned long)dst < (unsigned long)src) {
        /*
         * Copy forward.
         */
        t = (long)src;  /* only need low bits */
        if ((t | (long)dst) & wmask) {
            /*
             * Try to align operands.  This cannot be done
             * unless the low bits match.
             */
            if ((t ^ (long)dst) & wmask || length < wsize)
                t = length;
            else
                t = wsize - (t & wmask);
            length -= t;
            TLOOP1(*dst++ = *src++);
        }
        /*
         * Copy whole words, then mop up any trailing bytes.
         */
        t = length / wsize;
        TLOOP(*(word *)dst = *(word *)src; src += wsize; dst += wsize);
        t = length & wmask;
        TLOOP(*dst++ = *src++);
    } else {
        /*
         * Copy backwards.  Otherwise essentially the same.
         * Alignment works as before, except that it takes
         * (t&wmask) bytes to align, not wsize-(t&wmask).
         */
        src += length;
        dst += length;
        t = (long)src;
        if ((t | (long)dst) & wmask) {
            if ((t ^ (long)dst) & wmask || length <= wsize)
                t = length;
            else
                t &= wmask;
            length -= t;
            TLOOP1(*--dst = *--src);
        }
        t = length / wsize;
        TLOOP(src -= wsize; dst -= wsize; *(word *)dst = *(word *)src);
        t = length & wmask;
        TLOOP(*--dst = *--src);
    }
done:
#if defined(MEMPCPY)
    return ((void *)(((char *)dst0) + len));
#else
    return;
#endif
}
