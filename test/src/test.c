#include <stdlib.h>
#include <stdio.h>

void ding(void) { printf("DING!\n"); }
void dong(void) { printf("DONG!\n"); }

int main(int argc, char **argv) {
    ding();
    dong();
    ding();
    dong();
    return 0;
}
