package main

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"sync"
)

func httpHandler(w http.ResponseWriter, r *http.Request) {
	// Print "Hello from env variable IDENTITY" if set, otherwise print a default message
	identity := os.Getenv("IDENTITY")
	if identity != "" {
		fmt.Fprintf(w, "Hello from %s!\n", identity)
	} else {
		fmt.Fprintln(w, "Hello from the Go HTTP server!")
	}
}

func startUDPServer(wg *sync.WaitGroup) {
	defer wg.Done()

	addr := net.UDPAddr{
		Port: 9090,
		IP:   net.ParseIP("0.0.0.0"),
	}

	conn, err := net.ListenUDP("udp", &addr)
	if err != nil {
		fmt.Println("Error starting UDP server:", err)
		os.Exit(1)
	}
	defer conn.Close()

	fmt.Println("UDP server is running on port 9090...")

	buffer := make([]byte, 1024)
	for {
		n, remoteAddr, err := conn.ReadFromUDP(buffer)
		if err != nil {
			fmt.Println("Error reading from UDP:", err)
			continue
		}
		fmt.Printf("Received from %s: %s\n", remoteAddr, string(buffer[:n]))

		// Echo back the message
		_, err = conn.WriteToUDP([]byte("Echo: "+string(buffer[:n])), remoteAddr)
		if err != nil {
			fmt.Println("Error responding to UDP client:", err)
		}
	}
}

func main() {
	var wg sync.WaitGroup

	// Start UDP server in a separate goroutine
	wg.Add(1)
	go startUDPServer(&wg)

	// Start HTTP server
	http.HandleFunc("/", httpHandler)
	fmt.Println("HTTP server is running on port 8080...")
	http.ListenAndServe(":8080", nil)

	wg.Wait() // Ensure goroutine doesn't exit
}
