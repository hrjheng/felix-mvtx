hexdump ../../../data/data_20200812.raw  -v -e '"%08_ax: "' -e '10/1 "%02x-" 6/1 "%02x"' -e '"\n"' | head -n 100
