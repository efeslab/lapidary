#define _GNU_SOURCE
#include <unistd.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>

void _gdb_expr() {
    /* printf( "\n-------- c code -----2\n" ); */
    char buf[BUFSIZ] = {'\0'};
    uint64_t addr = 0;
    addr = (uint64_t)sbrk(0);
    int fd = open("/tmp/sbrk.txt", O_CREAT | O_APPEND | O_WRONLY, 0666);
    /* char* err = strerror( errno ); */
    /* printf( "last error %s\n", err ); */
    write(fd, &addr, BUFSIZ);
    close(fd);
    /* printf( "\n-------- leaving c code ----- fd = %d\n", fd ); */
}
