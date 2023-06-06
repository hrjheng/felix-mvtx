#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv) {
  FILE *fp;
  int k, id, packet_counter, ep_id;
  int counter[32] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
  int word = 0;
  int size;
  int registered[32] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
  int ev[32] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
  int tot_ev = 0;

  int max_ev[32];

  int i,j;
  int skip_next_link[32] = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
  int event=0;

  for (j = 0;j < 31; j++)
    max_ev[j] = 100000000;

  fp = fopen(argv[1], "rb");

  while(!feof(fp)) {

    fread (&k, sizeof(int), 1, fp);

    if (word == 3) {
      id = k & 0xff;
      packet_counter = (k >> 8) & 0xff;
      ep_id = k >> 28;
      id = id + (12 * ep_id);
      if (skip_next_link[id] == 0 && counter[id] != packet_counter) {
          printf("ERROR %d %d - EXP: %x RD : %x \n", id, ev[id], counter[id], packet_counter);
          max_ev[id] = ev[id];
          skip_next_link[id] = 1;
        }
        counter[id] += 1;
        if (counter[id] == 256)
          counter[id] = 0;
    }

    word++;
    word %= 2048;
    if (word == 0) {
      ev[id]++;
      tot_ev++;
      event++;
    }
  }

  printf("EV analysed %d \n");

  for (i=0; i<32 ; i++) {
    printf("ev[%d] = %d - %d\n", i, ev[i], max_ev[i]);
  }

  fclose(fp);
}

