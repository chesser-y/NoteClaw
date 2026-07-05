// Source: CodeSearchNet go test split
// Repository: etcd-io/etcd
// Function: mustWaitPinReady
// Documentation: // mustWaitPinReady waits up to 3-second until connection is up (pin endpoint).
// Fatal on time-out.
func mustWaitPinReady(t *testing.T, cli *clientv3.Client) {
	// TODO: decrease timeout after balancer rewrite!!!
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	_, err := cli.Get(ctx, "foo")
	cancel()
	if err != nil {
		t.Fatal(err)
	}
}
