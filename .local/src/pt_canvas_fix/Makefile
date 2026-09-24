CC ?= gcc
CFLAGS ?= -O2 -fPIC -Wall -Wextra
LDFLAGS ?= -shared -ldl
TARGET ?= $(HOME)/.local/lib/libpt_canvas_fix.so

all: $(TARGET)

$(TARGET): pt_canvas_fix.c
	mkdir -p $(dir $(TARGET))
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean
