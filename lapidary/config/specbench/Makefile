.PHONY: all default clean install

SRC17=src
SPEC17_ROOT=$(abspath ../spec-cpu2017)
SPEC17_BENCH=$(foreach b, $(wildcard $(SRC17)/*), $(shell basename $(b)))
SPEC17_TARGETS=$(foreach b, $(SPEC17_BENCH), build-spec17-$(b))

default: all

build-setup:
	@mkdir -p bin/

all: all-spec17

define SPEC2017BUILD
build-spec17-$(1): build-setup
	@echo invoking "build-spec17-$1"
	make SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		make TARGET=povray_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		make TARGET=wrf_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		make TARGET=blender_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		make TARGET=cam4_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		make TARGET=imagick_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean || \
		(make TARGET=x264_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean && \
		make TARGET=ldecod_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) clean)
	make SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		make TARGET=povray_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		make TARGET=wrf_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		make TARGET=blender_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		make TARGET=cam4_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		make TARGET=imagick_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) || \
		(make TARGET=x264_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1) && \
		make TARGET=ldecod_r SPEC=$(SPEC17_ROOT) -C $(SRC17)/$(1))
	sync
	cp -v $(shell find -L $(SRC17)/$(1) -type f -executable -exec file -F '' \
		-i '{}' \; | grep 'charset=binary' | cut -f 1 -d ' ' | paste -sd ' ' -) bin/
endef

$(foreach b, $(SPEC17_BENCH), $(eval $(call SPEC2017BUILD,$(b))))

all-spec17: $(SPEC17_TARGETS)

clean:
	@rm -rfv *.TBL *.formatted *d01* *.input *.output *.ini *.pov
	@rm -rfv *.of *_DATA *DOMAIN* *.tga *.tbl *.prm *.TBLa
	@rm -rfv tr49t67 tr49t85 tr67t85 ned/ co2_trans gribmap.txt BuckBunny.264
	@rm -rfv *.vtk dataDec.txt spec_ref.par statistics *.nc *.stream.txt
	@rm -rfv log log.dec log.txt gx3v7_* *.nml *.rc *.log *.ieeer8 *.ieeei4
	@rm -rfv x264.out HorizontalSanity.txt *.xl dice_* dlnd_* drv_* atm_in
	@rm -rfv blender_* datm_* pop2_* puzzles.txt *clim.x0.5.txt *.out 1am0 *.m
	@rm -rfv *.def *.dat fort.9 fotonik3d_r
