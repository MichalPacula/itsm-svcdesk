<!-- ai-generated: 50% - Claude Code ran the measurement and drafted the text from the numbers; I reviewed it -->
# Client-server gap (Stretch 2)

I put Toxiproxy in front of `svcdesk` with one downstream latency toxic of 100 ms and 10 ms jitter, and ran the M-08
load through the proxy (open-loop, 40 requests/s, 60 s). The client's p99 (oha) was 297.2 ms; the p99 that my own
histogram reports for the same run was 196.5 ms. The gap is 100.7 ms, which is the toxic: 100 ms of added delay plus
a small amount of jitter in the tail.

The server's histogram cannot see the gap because it starts its timer when the ASGI request reaches the application
and stops it when the response has been handed to the transport. Toxiproxy sits outside the process, between the
client and the socket, and delays the bytes on their way back; from `svcdesk`'s point of view the request was answered
as fast as `kb-index` allowed (the slow mode near 0.2 s). The client, however, measures from the scheduled instant to the
last byte, so every request also pays the toxic. A server-side histogram therefore always understates what a user
sees by whatever the network, proxies and queues in front of the process add. An SLO measured only on the server would
declare a service healthy while the client's p99 is 50 % higher; it would have to be measured at the edge (a load
balancer or probe) to include that part.
