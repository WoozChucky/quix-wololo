using k8s.KubeConfigModels;

namespace WriteHelloWorld;

public class K8SConfigGenerator
{
    public static K8SConfiguration Generate(string clusterName, string clusterEndpoint, string clusterCA,
        string clientCA, string clientKey, string token)
    {
        return new K8SConfiguration()
        {
            ApiVersion = "v1",
            Kind = "Config",
            CurrentContext = clusterName,
            Clusters = new List<Cluster>
            {
                new()
                {
                    Name = clusterName,
                    ClusterEndpoint = new ClusterEndpoint
                    {
                        Server = clusterEndpoint,
                        CertificateAuthorityData = clusterCA
                    }
                }
            },
            Contexts = new List<Context>
            {
                new()
                {
                    Name = clusterName,
                    ContextDetails = new ContextDetails
                    {
                        Cluster = clusterName,
                        User = clusterName
                    }
                }
            },
            Users = new List<User>()
            {
                new()
                {
                    Name = clusterName,
                    UserCredentials = new UserCredentials
                    {
                        ClientCertificateData = clientCA,
                        ClientKeyData = clientKey,
                        Token = token
                    }
                }
            },
            Preferences = new Dictionary<string, object>(),
        };
    }
}
