#!/bin/sh
PW_PATH=/home
if [ ! -d $PW_PATH/logs ]; then
    mkdir $PW_PATH/logs
fi

cd $PW_PATH/logservice; ./logservice logservice.conf >$PW_PATH/logs/logservice.log 2>&1 &
sleep 1

cd $PW_PATH/uniquenamed; ./uniquenamed gamesys.conf >$PW_PATH/logs/uniquenamed.log 2>&1 &
sleep 1

cd $PW_PATH/authd; ./authd >$PW_PATH/logs/authd.log 2>&1 &
sleep 3

cd $PW_PATH/gamedbd; ./gamedbd gamesys.conf >$PW_PATH/logs/gamedbd.log 2>$PW_PATH/logs/gamedbd.err.log &
sleep 1

cd $PW_PATH/gacd; ./gacd gamesys.conf >$PW_PATH/logs/gacd.log 2>&1 &
sleep 1

cd $PW_PATH/gfactiond; ./gfactiond gamesys.conf >$PW_PATH/logs/gfactiond.log 2>&1 &
sleep 1

cd $PW_PATH/gdeliveryd; ./gdeliveryd gamesys.conf >$PW_PATH/logs/gdeliveryd.log 2>/dev/null &
sleep 1

cd $PW_PATH/glinkd; ./glinkd gamesys.conf 1 >$PW_PATH/logs/glink.log 2>&1 &
cd $PW_PATH/glinkd; ./glinkd gamesys.conf 2 >$PW_PATH/logs/glink2.log 2>&1 &
sleep 3

cd $PW_PATH/gamed; LD_PRELOAD="./pw_expfix_155.so ./pw_instance_watch.so" ./gs gs01 gs.conf gmserver.conf gsalias.conf is61 >$PW_PATH/logs/gs01.log 2>&1 &
sleep 30

#cd $PW_PATH/gamed; ./gs arena01 arena02 arena03 arena04 is01 is02 is05 is06 is07 is08 is09 is10 is11 is12 is13 is14 is15 is16 is17 is18 is19 is20 is21 is22 is23 is24 is25 is26 is27 is28 is29 is31 is32 is33 bg01 bg02 bg03 bg04 bg05 bg06 >$PW_PATH/logs/game_all.log 2>&1 &
sleep 10
