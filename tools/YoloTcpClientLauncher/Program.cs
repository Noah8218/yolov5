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
    ?? ResolveDefaultImageRoot(projectRoot);
string host = GetOption(args, "--host") ?? "127.0.0.1";
string port = GetOption(args, "--port") ?? "5000";
string confidence = GetOption(args, "--conf") ?? "0.25";
string imageSize = GetOption(args, "--img-size")
    ?? GetOption(args, "--image-size")
    ?? "320";
string device = GetOption(args, "--device") ?? "";
string ensureEnvironmentScript = Path.Combine(projectRoot, "launchers", "ensure-yolo-environment.ps1");
bool installRequirements = HasFlag(args, "--install-requirements");
bool promptInstall = HasFlag(args, "--prompt-install");

if ((installRequirements || promptInstall) && File.Exists(ensureEnvironmentScript))
{
    int setupExitCode = RunEnvironmentSetup(
        ensureEnvironmentScript,
        projectRoot,
        installRequirements ? "-InstallIfMissing" : "-PromptInstall");
    if (setupExitCode != 0)
    {
        return setupExitCode;
    }
}
else if (!File.Exists(pythonExe) && File.Exists(ensureEnvironmentScript))
{
    Console.WriteLine($"Python virtual environment not found: {pythonExe}");
    Console.WriteLine("Run setup before starting the worker:");
    Console.WriteLine($"powershell -NoProfile -ExecutionPolicy Bypass -File \"{ensureEnvironmentScript}\" -InstallIfMissing");
    Console.WriteLine("Or launch this tool with --install-requirements.");
    Console.WriteLine();
    return 12;
}

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
AddArg(process, "--img-size", imageSize);
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
Console.WriteLine($"Image size   : {imageSize}");
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

static string ResolveDefaultImageRoot(string projectRoot)
{
    foreach (string candidate in new[]
    {
        Path.Combine(projectRoot, "data", "train", "images"),
        Path.Combine(projectRoot, "data", "valid", "images"),
        Path.Combine(projectRoot, "data", "images"),
        @"C:\Git\py\data\train\images",
        @"C:\Git\py\KtemData"
    })
    {
        if (Directory.Exists(candidate))
        {
            return candidate;
        }
    }

    return @"C:\Git\py\data\train\images";
}

static int RunEnvironmentSetup(string scriptPath, string projectRoot, string setupMode)
{
    using var process = new Process();
    process.StartInfo.FileName = "powershell";
    process.StartInfo.WorkingDirectory = projectRoot;
    process.StartInfo.UseShellExecute = false;
    process.StartInfo.ArgumentList.Add("-NoProfile");
    process.StartInfo.ArgumentList.Add("-ExecutionPolicy");
    process.StartInfo.ArgumentList.Add("Bypass");
    process.StartInfo.ArgumentList.Add("-File");
    process.StartInfo.ArgumentList.Add(scriptPath);
    process.StartInfo.ArgumentList.Add("-ProjectRoot");
    process.StartInfo.ArgumentList.Add(projectRoot);
    process.StartInfo.ArgumentList.Add(setupMode);

    process.Start();
    process.WaitForExit();
    return process.ExitCode;
}
