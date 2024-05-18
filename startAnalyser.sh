
#!/bin/sh

set -e

cd /home/debian/PSS
QTAPP="Analyser.py"
QTAPPSTART="python3 Analyser.py > /var/log/Xsession.log 2>&1"

case "$1" in
  start)
	echo "Starting ${QTAPP}"
	Xorg &
	export DISPLAY=:0
	eval $QTAPPSTART &

	;;
  stop)
	echo "Stopping ${QTAPP}"
		kill `/bin/ps ax| grep $QTAPP | grep -v "grep" | awk '{print $1}'`
		kill `/bin/ps ax| grep "Xorg" | grep -v "grep" | awk '{print $1}'`
	;;
  restart)
	$0 stop
	$0 start
	;;
  *)
	echo "usage: $0 { start | stop | restart }" >&2
	exit 1
	;;
esac

exit 0
