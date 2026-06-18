using System.Diagnostics;

string projectRoot = Path.GetFullPath(
    GetOption(args, "--project-root")
    ?? Environment.GetEnvironmentVariable("YOLO_WORKER_ROOT")
    ?? @"C:\Git\yolov5");

string pythonExe = GetOption(args, "--python")
    ?? Path.Combine(projectRoot, ".venv", "Scripts", "python.exe");
string clientScript = GetOption(args, "--script")
    ?? Path.Combine(projectRoot, "labeling_tcp_client.py");
string weightsPath = GetOption(args, "--weights")
    ?? Path.Combine(projectRoot, "best.pt");
string modelRoot = GetOption(args, "--model-root")
    ?? Path.Combine(projectRoot, "yolov5Master");
string imageRoot = GetOption(args, "--image-root")
    ?? Environment.GetEnvironmentVariable("YOLO_IMAGE_ROOT")
    ?? @"C:\Git\py\KtemData";
string host = GetOption(args, "--host") ?? "127.0.0.1";
string port = GetOption(args, "--port") ?? "5000";
string confidence = GetOption(args, "--conf") ?? "0.25";
string device = GetOption(args, "--device") ?? "";

if (!File.Exists(clientScript))
{
    string legacyScript = Path.Combine(projectRoot, "labelling_tcp_client.py");
    if (File.Exists(legacyScript))
    {
        clientScript = legacyScript;
    }
}

ValidateFile(pythonExe, "Python executable");
ValidateFile(clientScript, "TCP client script");
ValidateFile(weightsPath, "YOLO weights");
ValidateDirectory(modelRoot, "YOLO model root");

if (!Directory.Exists(imageRoot))
{
    Console.WriteLine($"Warning: image root not found: {imageRoot}");
    Console.WriteLine("Absolute image paths in DetectImage requests will still work.");
}

using var process = new Process();
process.StartInfo.FileName = pythonExe;
process.StartInfo.WorkingDirectory = projectRoot;
process.StartInfo.UseShellExecute = false;

AddArg(process, clientScript);
AddArg(process, "--host", host);
AddArg(process, "--port", port);
AddArg(process, "--weights", weightsPath);
AddArg(process, "--model-root", modelRoot);
AddArg(process, "--image-root", imageRoot);
AddArg(process, "--conf", confidence);
AddArg(process, "--retry");

if (!string.IsNullOrWhiteSpace(device))
{
    AddArg(process, "--device", device);
}

if (HasFlag(args, "--preload"))
{
    AddArg(process, "--preload");
}

Console.WriteLine("Starting YOLOv5 labeling AI worker.");
Console.WriteLine($"Project root : {projectRoot}");
Console.WriteLine($"Python       : {pythonExe}");
Console.WriteLine($"Script       : {clientScript}");
Console.WriteLine($"Weights      : {weightsPath}");
Console.WriteLine($"Model root   : {modelRoot}");
Console.WriteLine($"Image root   : {imageRoot}");
Console.WriteLine($"TCP target   : {host}:{port}");
Console.WriteLine();

process.Start();
process.WaitForExit();
return process.ExitCode;

static string? GetOption(string[] args, string name)
{
    for (int i = 0; i < args.Length - 1; i++)
    {
        if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
        {
            return args[i + 1];
        }
    }

    return null;
}

static bool HasFlag(string[] args, string name)
{
    return args.Any(arg => string.Equals(arg, name, StringComparison.OrdinalIgnoreCase));
}

static void AddArg(Process process, params string[] values)
{
    foreach (string value in values)
    {
        process.StartInfo.ArgumentList.Add(value);
    }
}

static void ValidateFile(string path, string name)
{
    if (!File.Exists(path))
    {
        throw new FileNotFoundException($"{name} not found.", path);
    }
}

static void ValidateDirectory(string path, string name)
{
    if (!Directory.Exists(path))
    {
        throw new DirectoryNotFoundException($"{name} not found: {path}");
    }
}
