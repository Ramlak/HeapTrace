#include <stdio.h>
#include <stdlib.h>

int main()
{
	int x;
	do
	{
		scanf("%d", &x);
		void * p = malloc(x);
		printf("%p\n", p);
		free(p);
	}
	while(x);

	return 0;
} 
