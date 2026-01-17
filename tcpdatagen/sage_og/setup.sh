mods=( tcp_bbr tcp_bbr1 tcp_bic tcp_cdg tcp_cubic tcp_htcp tcp_highspeed tcp_hybla tcp_illinois tcp_newreno tcp_vegas tcp_veno tcp_westwood tcp_yeah )

for m in "${mods[@]}"; do
  sudo modprobe  "$m"  || echo "Note: $m not found for this kernel."
done