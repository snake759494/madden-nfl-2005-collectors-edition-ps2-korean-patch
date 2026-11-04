/* mtenc 프레임 출력 -> 디코더가 실제로 소비하는 바이트 경계에 맞춰 Rev3 프레임 재배치.
   출력: 프레임마다 u16 L + L바이트 (프레임 데이터 + 뒤따르는 플래그 바이트) */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "utk.h"
int main(int argc, char **argv) {
    FILE *in = fopen(argv[1], "rb"), *out = fopen(argv[2], "wb");
    static uint8_t buf[4096]; UTKContext u; utk_init(&u);
    unsigned char h[2];
    while (fread(h, 1, 2, in) == 2) {
        unsigned n = h[0] | h[1] << 8, nb = (n + 7) / 8, L;
        memset(buf, 0, sizeof buf);
        if (fread(buf, 1, nb, in) != nb) return 1;
        utk_set_ptr(&u, buf, buf + sizeof buf);
        utk_decode_frame(&u);
        L = (unsigned)(u.ptr - buf) - 1;  /* rev3: 마지막 8비트 되돌림 */
        /* L 이 프레임 데이터 길이, buf[L] 이 다음 플래그 */
        if (buf[L] == 0xee) { fprintf(stderr, "flag clash\n"); return 2; }
        L += 1;
        h[0] = L & 0xff; h[1] = L >> 8; fwrite(h, 1, 2, out); fwrite(buf, 1, L, out);
    }
    fclose(out); return 0;
}
