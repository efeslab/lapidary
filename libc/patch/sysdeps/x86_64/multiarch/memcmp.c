/* Multiple versions of memcmp.
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
# define memcmp __redirect_memcmp
# include <string.h>
# undef memcmp

# define SYMBOL_NAME memcmp
# include "ifunc-memcmp.h"

libc_ifunc_redirected (__redirect_memcmp, memcmp, IFUNC_SELECTOR ());
# undef bcmp
weak_alias (memcmp, bcmp)

# ifdef SHARED
__hidden_ver1 (memcmp, __GI_memcmp, __redirect_memcmp)
  __attribute__ ((visibility ("hidden"))) __attribute_copy__ (memcmp);
# endif
#endif

typedef long unsigned int size_t;
int
__memcmp_sgx(const void *s1, const void *s2, size_t n)
{
    if (n != 0) {
        const unsigned char *p1 = (const unsigned char *)s1;
        const unsigned char *p2 = (const unsigned char *)s2;

        do {
            if (*p1++ != *p2++)
                return (*--p1 - *--p2);
        } while (--n != 0);
    }
    return (0);
}

#include <wchar.h>
int
__wmemcmp_sgx(const wchar_t *s1, const wchar_t *s2, size_t n)
{
	size_t i;

	for (i = 0; i < n; i++) {
		if (*s1 != *s2) {
			/* wchar might be unsigned */
			return *s1 >
			       *s2 ? 1 : -1;
		}
		s1++;
		s2++;
	}
	return 0;
}
