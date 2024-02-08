using System.Text.Json;
using k8s;
using k8s.Models;
using QuixStreams.Streaming;
using WriteHelloWorld;

internal class Program
{
    private static Kubernetes _kubernetesClient;
    private static IQuixStreamingClientAsync _quixClient;
    private static CancellationTokenSource _cancellationTokenSource = new CancellationTokenSource();
    
    private static Dictionary<string, DateTime> _lastProcessedTimestamps = new Dictionary<string, DateTime>();
    
    private static async Task Main(string[] args)
    {
        AppDomain.CurrentDomain.UnhandledException += CurrentDomainOnUnhandledException;
        AppDomain.CurrentDomain.ProcessExit += CurrentDomainOnProcessExit;

        _quixClient = new QuixStreamingClient();
        
        var outputTopicName = Environment.GetEnvironmentVariable("output-metrics") ?? "k8s-metrics";
            
        using var producer = await _quixClient.GetTopicProducerAsync(outputTopicName);
        
        var clusterName = Environment.GetEnvironmentVariable("K8SClusterName") ?? throw new InvalidOperationException("K8SClusterName is not set. Please set it in the environment variables.");
        var clusterEndpoint = Environment.GetEnvironmentVariable("K8SEndpoint") ?? throw new InvalidOperationException("K8SEndpoint is not set. Please set it in the environment variables.");
        var clusterCA = Environment.GetEnvironmentVariable("K8SClusterCertificateAuthorityData") ?? throw new InvalidOperationException("K8SClusterCertificateAuthorityData is not set. Please set it in the environment variables.");
        var clientCA = Environment.GetEnvironmentVariable("K8SClientCertificateData") ?? throw new InvalidOperationException("K8SClientCertificateData is not set. Please set it in the environment variables.");
        var clientKey = Environment.GetEnvironmentVariable("K8SClientKeyData") ?? throw new InvalidOperationException("K8SClientKeyData is not set. Please set it in the environment variables.");
        var clientToken = Environment.GetEnvironmentVariable("K8SToken") ?? throw new InvalidOperationException("K8SToken is not set. Please set it in the environment variables.");
        
        var namespaceName = Environment.GetEnvironmentVariable("K8S_NAMESPACE") ?? "default";
        
        var k8sConfig = K8SConfigGenerator.Generate(clusterName, clusterEndpoint, clusterCA, clientCA, clientKey, clientToken);

        _kubernetesClient = new Kubernetes(KubernetesClientConfiguration.BuildConfigFromConfigObject(k8sConfig));
        
        var stream = producer.CreateStream();
        stream.Properties.Name = $"k8s-metrics [{namespaceName} namespace]";
        stream.Timeseries
            .AddDefinition("pod", "pod", "The name of the pod")
            .AddDefinition("namespace", "namespace", "The name of the namespace")
            .AddDefinition("container", "container", "The name of the container")
            .AddDefinition("cpu", "cpu", "The CPU usage of the container").SetUnit("nanocores")
            .AddDefinition("memory", "memory", "The memory usage of the container").SetUnit("bytes");
        
        Console.WriteLine("All metrics are being streamed to QuixStreams");
        
        while (!_cancellationTokenSource.IsCancellationRequested)
        {
            var metrics = await GetMetrics(namespaceName);
    
            foreach (var metric in metrics)
            {
                var collectedAt = metric.Timestamp;
                
                foreach (var container in metric.Containers)
                {
                    var key = $"{metric.Metadata.Name}-{metric.Metadata.NamespaceProperty}-{container.Name}";
                    DateTime lastProcessedTimestamp;
                    _lastProcessedTimestamps.TryGetValue(key, out lastProcessedTimestamp);

                    if (!(collectedAt > lastProcessedTimestamp)) continue;
                    
                    var builder = stream.Timeseries.Buffer
                        .AddTimestamp(DateTime.UtcNow)
                        .AddValue("pod", metric.Metadata.Name)
                        .AddValue("namespace", metric.Metadata.NamespaceProperty)
                        .AddValue("container", container.Name);
                    foreach (var metricValue in container.Usage)
                    {
                        var metricKey = metricValue.Key!;
                        var metricValueKey = metricValue.Value!.ToDouble();
                        if (metricKey == "cpu")
                        {
                            metricValueKey *= 1000000000;
                        }
                        builder.AddValue(metricKey, metricValueKey);
                    }

                    builder.Publish();

                    _lastProcessedTimestamps[key] = collectedAt.Value;
                }
            }
        }
    }

    private static async Task<IEnumerable<string>> GetNamespaces()
    {
        var namespaces = await _kubernetesClient.ListNamespaceAsync(cancellationToken: _cancellationTokenSource.Token);
        return namespaces.Items.Select(n => n.Metadata.Name);
    }
    
    private static async Task<IEnumerable<PodMetrics>> GetMetrics(string namespaceName)
    {
        var metricsJson = (JsonElement) await _kubernetesClient.CustomObjects.GetNamespacedCustomObjectAsync(
            "metrics.k8s.io", 
            "v1beta1", 
            namespaceName, 
            "pods", // "nodes"
            string.Empty, 
            cancellationToken: _cancellationTokenSource.Token
        );

        var metrics = metricsJson.Deserialize<PodMetricsList>();
        return metrics!.Items;
    }
    
    private static void CurrentDomainOnUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        Console.WriteLine("Unhandled exception: " + e.ExceptionObject);
    }

    private static void CurrentDomainOnProcessExit(object? sender, EventArgs e)
    {
        _cancellationTokenSource.Cancel();
        Console.WriteLine("Process is exiting");
    }
}
