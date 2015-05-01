#include <stdlib.h>

int main()
{
	void * x[4];
	int i;
	for(i = 0; i < 4; i++)
		x[i] = malloc(0x100);
	free(x[0]);
	free(x[2]);
	return 0;
}