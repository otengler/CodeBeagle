del anim*.png
del update.gif

convert update.png -virtual-pixel transparent -distort SRT '0' anim1.png
convert update.png -virtual-pixel transparent -distort SRT '15' anim2.png
convert update.png -virtual-pixel transparent -distort SRT '30' anim3.png
convert update.png -virtual-pixel transparent -distort SRT '45' anim4.png
convert update.png -virtual-pixel transparent -distort SRT '60' anim5.png
convert update.png -virtual-pixel transparent -distort SRT '75' anim6.png
convert update.png -virtual-pixel transparent -distort SRT '90' anim7.png
convert update.png -virtual-pixel transparent -distort SRT '105' anim8.png
convert update.png -virtual-pixel transparent -distort SRT '120' anim9.png
convert update.png -virtual-pixel transparent -distort SRT '135' anim10.png
convert update.png -virtual-pixel transparent -distort SRT '150' anim11.png
convert update.png -virtual-pixel transparent -distort SRT '165' anim12.png
convert update.png -virtual-pixel transparent -distort SRT '180' anim13.png
convert update.png -virtual-pixel transparent -distort SRT '195' anim14.png
convert update.png -virtual-pixel transparent -distort SRT '210' anim15.png
convert update.png -virtual-pixel transparent -distort SRT '225' anim16.png
convert update.png -virtual-pixel transparent -distort SRT '240' anim17.png
convert update.png -virtual-pixel transparent -distort SRT '255' anim18.png
convert update.png -virtual-pixel transparent -distort SRT '270' anim19.png
convert update.png -virtual-pixel transparent -distort SRT '285' anim20.png
convert update.png -virtual-pixel transparent -distort SRT '300' anim21.png
convert update.png -virtual-pixel transparent -distort SRT '315' anim22.png
convert update.png -virtual-pixel transparent -distort SRT '330' anim23.png
convert update.png -virtual-pixel transparent -distort SRT '345' anim24.png

convert -verbose -dispose previous -delay 20 -loop 0 anim1.png anim2.png anim3.png anim4.png anim5.png anim6.png anim7.png anim8.png anim9.png anim10.png anim11.png anim12.png anim13.png anim14.png anim15.png anim16.png anim17.png anim18.png anim19.png anim20.png anim21.png anim22.png anim23.png anim24.png update.gif

del anim*.png