/* Multiple versions of memcpy.
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
# define memcpy __redirect_memcpy
# include <string.h>
# undef memcpy

# define SYMBOL_NAME memcpy


# include "ifunc-memmove.h"

libc_ifunc_redirected (__redirect_memcpy, __new_memcpy,
		       IFUNC_SELECTOR ());

# ifdef SHARED
__hidden_ver1 (__new_memcpy, __GI_memcpy, __redirect_memcpy)
  __attribute__ ((visibility ("hidden")));
# endif



# include <shlib-compat.h>
versioned_symbol (libc, __new_memcpy, memcpy, GLIBC_2_14);
#endif

/*
 * sizeof(word) MUST BE A POWER OF TWO
 * SO THAT wmask BELOW IS ALL ONES
 */
typedef	long word;		/* "word" used for optimal copy speed */

#define	wsize	sizeof(word)
#define	wmask	(wsize - 1)


typedef long unsigned int size_t;

/*
 * Copy a block of memory, not handling overlap.
 */
void *
__memcpy_sgx(void *dst0, const void *src0, size_t length)
{
	char *dst = (char *)dst0;
	const char *src = (const char *)src0;
	size_t t;

	if (length == 0 || dst == src)		/* nothing to do */
		goto done;

	if ((dst < src && dst + length > src) ||
	    (src < dst && src + length > dst)) {
        /* backwards memcpy */
	    return (void*)0;
    }

	/*
	 * Macros: loop-t-times; and loop-t-times, t>0
	 */
#define	TLOOP(s) if (t) TLOOP1(s)
#define	TLOOP1(s) do { s; } while (--t)

	/*
	 * Copy forward.
	 */
	t = (long)src;	/* only need low bits */
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
done:
	return (dst0);
}

