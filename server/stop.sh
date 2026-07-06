#!/bin/sh
WAIT_GS=30
WAIT_DELIVERY=10
WAIT_DB=10

pkill -15 gs
sleep $WAIT_GS

pkill -15 gdeliveryd
sleep $WAIT_DELIVERY

pkill -15 gamedbd
sleep $WAIT_DB

pkill -9 gfactiond
pkill -9 glinkd
pkill -9 uniquenamed
pkill -9 authd
pkill -9 gacd
pkill -9 logservice
pkill -9 java

pkill -9 gs
pkill -9 gdeliveryd
pkill -9 gamedbd

echo Stopped.
