#include <stdlib.h>
#include <stdio.h>
#include <time.h>

int main(int argc, char const *argv[])
{
	srand(time(NULL));
	int size = rand() % 0x400;

	void * mem = malloc(size);
	printf("%p (%d)\n", mem, size);
	free(mem);

	return 0;
}