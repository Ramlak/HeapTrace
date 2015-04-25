#include <stdio.h>
#include <stdlib.h>

int main()
{
	int x;
	do
	{
		scanf("%d", &x);
		void * p = malloc(x);
		free(p);
	}
	while(x);

	return 0;
} 
