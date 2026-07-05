# Source: CodeSearchNet ruby test split
# Repository: Shopify/kubernetes-deploy
# Function: KubernetesDeploy.KubernetesResource.fetch_events
# Documentation: Returns a hash in the following format:
 {
   "pod/web-1" => [
     "Pulling: pulling image "hello-world:latest" (1 events)",
     "Pulled: Successfully pulled image "hello-world:latest" (1 events)"
   ]
 }
def fetch_events(kubectl)
      return {} unless exists?
      out, _err, st = kubectl.run("get", "events", "--output=go-template=#{Event.go_template_for(type, name)}",
        log_failure: false)
      return {} unless st.success?

      event_collector = Hash.new { |hash, key| hash[key] = [] }
      Event.extract_all_from_go_template_blob(out).each_with_object(event_collector) do |candidate, events|
        events[id] << candidate.to_s if candidate.seen_since?(@deploy_started_at - 5.seconds)
      end
    end
