/* Multiple versions of strchr.
   All versions must be listed in ifunc-impl-list.c.
   Copyright (C) 2009-2019 Free Software Foundation, Inc.
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
# define strchr __redirect_strchr
# include <string.h>
# undef strchr

# define SYMBOL_NAME strchr
# include <init-arch.h>

extern __typeof (REDIRECT_NAME) OPTIMIZE (sse2) attribute_hidden;
extern __typeof (REDIRECT_NAME) OPTIMIZE (sgx) attribute_hidden;
extern __typeof (REDIRECT_NAME) OPTIMIZE (sse2_no_bsf) attribute_hidden;
extern __typeof (REDIRECT_NAME) OPTIMIZE (avx2) attribute_hidden;

extern volatile int ALWAYS_ONE;
static inline void *
IFUNC_SELECTOR (void)
{
  const struct cpu_features* cpu_features = __get_cpu_features ();

  if( ALWAYS_ONE )
    return OPTIMIZE(sgx);
  if (!CPU_FEATURES_ARCH_P (cpu_features, Prefer_No_VZEROUPPER)
      && CPU_FEATURES_ARCH_P (cpu_features, AVX2_Usable)
      && CPU_FEATURES_ARCH_P (cpu_features, AVX_Fast_Unaligned_Load))
    return OPTIMIZE (avx2);

  if (CPU_FEATURES_ARCH_P (cpu_features, Slow_BSF))
    return OPTIMIZE (sse2_no_bsf);

  return OPTIMIZE (sse2);
}

char *
__strchr_sgx(const char *p, int ch)
{
	char c = ch;
	for (;; ++p) {
		if (*p == c)
			return((char *)p);
		if (!*p)
			return ((char *)NULL);
	}
	/* NOTREACHED */
}

char *
__strchrnul_sgx(const char *p, int ch)
{
	char c = ch;
	for (;; ++p) {
		if (*p == c)
			return((char *)p);
		if (!*p)
			return ((char *)p);
	}
	/* NOTREACHED */
}

size_t
__strlen_sgx(const char *str)
{
	const char *s;

	for (s = str; *s; ++s)
		;
	return (s - str);
}

size_t
__strnlen_sgx(const char *str, size_t maxlen)
{
	const char *cp;

	for (cp = str; maxlen != 0 && *cp != '\0'; cp++, maxlen--)
		;

	return (size_t)(cp - str);
}

char *
__strrchr_sgx(const char *p, int ch)
{
	char *save;

	for (save = NULL;; ++p) {
		if (*p == ch)
			save = (char *)p;
		if (!*p)
			return(save);
	}
	/* NOTREACHED */
}

void *
__memchr_sgx(const void *s, int c, size_t n)
{
	if (n != 0) {
		const unsigned char *p = (const unsigned char *)s;

		do {
			if (*p++ == (unsigned char)c)
				return ((void *)(p - 1));
		} while (--n != 0);
	}
	return (NULL);
}

void *
__memrchr_sgx(const void *s, int c, size_t n)
{
	if (n != 0) {
		const unsigned char *p = (const unsigned char *)s + n;

		do {
			if (*--p == (unsigned char)c)
				return ((void *)(p));
		} while (--n != 0);
	}
	return (NULL);
}
    void *
__rawmemchr_sgx(const void *s, int c )
{
    const unsigned char *p = (const unsigned char *)s;

    do {
        if (*p++ == (unsigned char)c)
            return ((void *)(p - 1));
    } while (1);
}


wchar_t *
__wcschr_sgx(const wchar_t *s, wchar_t c)
{
	const wchar_t *p;

	p = s;
	for (;;) {
		if (*p == c) {
			return (wchar_t *)p;
		}
		if (!*p)
			return NULL;
		p++;
	}
	/* NOTREACHED */
}

int
__wcscmp_sgx(const wchar_t *s1, const wchar_t *s2)
{

	while (*s1 == *s2++)
		if (*s1++ == 0)
			return (0);
	/* XXX assumes wchar_t = int */
	return (*s1 - *--s2);
}

size_t
__wcslen_sgx(const wchar_t *s)
{
	const wchar_t *p;

	p = s;
	while (*p)
		p++;

	return p - s;
}

int
__wcsncmp_sgx(const wchar_t *s1, const wchar_t *s2, size_t n)
{

	if (n == 0)
		return (0);
	do {
		if (*s1 != *s2++) {
			/* XXX assumes wchar_t = int */
			return (*s1 - *--s2);
		}
		if (*s1++ == 0)
			break;
	} while (--n != 0);
	return (0);
}

wchar_t *
__wcsrchr_sgx(const wchar_t *s, wchar_t c)
{
	const wchar_t *p;

	p = s;
	while (*p)
		p++;
	while (s <= p) {
		if (*p == c) {
			return (wchar_t *)p;
		}
		p--;
	}
	return NULL;
}

wchar_t	*
__wmemchr_sgx(const wchar_t *s, wchar_t c, size_t n)
{
	size_t i;

	for (i = 0; i < n; i++) {
		if (*s == c) {
			return (wchar_t *)s;
		}
		s++;
	}
	return NULL;
}





libc_ifunc_redirected (__redirect_strchr, strchr, IFUNC_SELECTOR ());
weak_alias (strchr, index)
# ifdef SHARED
__hidden_ver1 (strchr, __GI_strchr, __redirect_strchr)
  __attribute__((visibility ("hidden"))) __attribute_copy__ (strchr);
# endif
#endif
