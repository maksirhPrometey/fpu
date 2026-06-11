#!/bin/sh
find /home/www/data/www.fpsu.org.ua/images -name "_1_20131202_1677194344.jpg" 2>/dev/null | head -3
find /sites/www.fpsu.org.ua/images -name "_1_20131202_1677194344.jpg" 2>/dev/null | head -3
ls -la /home/www/data/www.fpsu.org.ua/images/joomgallery/originals 2>/dev/null | head -3
du -sh /home/www/data/www.fpsu.org.ua/images/joomgallery 2>/dev/null
