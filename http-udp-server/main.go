package main

import (
	"fmt"
	"net"
	"net/http"
	"os"
	"github.com/vishvananda/netlink"
	"sync"
)

func httpHandler(w http.ResponseWriter, r *http.Request) {

	identity := os.Getenv("IDENTITY")
	if identity == "" {
		defaultInterface, err := getDefaultRouteInterface()
		if err != nil {
			fmt.Println("Error getting default interface:", err)
			identity = "unknown"
		} else {
			ip, err := getInterfaceIpAddress(defaultInterface)
			if err != nil {
				fmt.Println("Error getting default interface IP address:", err)
				identity = "unknown"
			} else {
				identity = ip.String()
			}
		}
	}

	fmt.Printf("Identity : %s\n", identity)
	
	fmt.Fprintf(w, "Hello from %s!\n", identity)
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

func getInterfaceIpAddress(interfaceName string) (net.IP, error) {
	iface, err := net.InterfaceByName(interfaceName)
	if err != nil {
		return nil, fmt.Errorf("could not find interface %s: %v", interfaceName, err)
	}

	addrs, err := iface.Addrs()
	if err != nil {
		return nil, fmt.Errorf("could not get addresses for interface %s: %v", interfaceName, err)
	}

	for _, addr := range addrs {
		if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() {
			return ipnet.IP, nil
		}
	}

	return nil, fmt.Errorf("no valid IP address found for interface %s", interfaceName)
}

func getDefaultRouteInterface() (string, error) {
	// List all routes
	routes, err := netlink.RouteList(nil, netlink.FAMILY_ALL)
	if err != nil {
		return "", fmt.Errorf("failed to list routes: %v", err)
	}

	/*
	fmt.Println("All routes:")
	for _, route := range routes {
		link, _ := netlink.LinkByIndex(route.LinkIndex)
		fmt.Printf("Dst: %v, Gw: %v, Dev: %v\n", route.Dst, route.Gw, link.Attrs().Name)
	}
	*/

	// Find the default route (Dst == nil)
	//fmt.Println("\nDefault route(s):")
	for _, route := range routes {
		if route.Dst.String() == "0.0.0.0/0" && route.Gw != nil {
			link, _ := netlink.LinkByIndex(route.LinkIndex)
			fmt.Printf("Default GW: %v, Egress Interface: %v\n", route.Gw, link.Attrs().Name)
			return link.Attrs().Name, nil
		}
	}
	return "", fmt.Errorf("no default route found")
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
