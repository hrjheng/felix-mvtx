(
echo $1 $2

TEST=$1
[ -z "$TEST" ] && exit 1

FILE=$2
[ -z "$FILE" ] && exit 1

#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8212
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8213
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8214
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8215
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8468
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8469
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8470
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8471
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8724
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8725
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8726
#time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8727
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8216
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8217
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8218
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8219
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8472
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8473
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8474
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8475
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8728
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8729
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8730
#time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8731

time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 0
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 256
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 512
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4099
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4355
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4611
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8198
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8199
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8454
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8455
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8710
time ddump -s -g -n 0 -p 2001 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8711
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 1
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 257
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 513
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4100
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4356
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 4612
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8200
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8201
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8456
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8457
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8712
time ddump -s -g -n 0 -p 2002 $FILE  | /home/mvtx/felix-mvtx/software/cpp/decoder/mvtx-decoder -p test -t $TEST -f 8713
)
