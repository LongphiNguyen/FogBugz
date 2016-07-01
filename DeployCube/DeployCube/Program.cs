using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

namespace DeployCube
{
    class Program
    {
        static void Main(string[] args)
        {
            string DEVENV = @"C:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\IDE\devenv.exe";
            string SOLUTION = @"C:\Cubes\FogBugz\FogBugz\FogBugz_2014\FogBugz_2014.sln";
            string PROJECTNAME = "FogBugz_2014";
            string BIN = @"C:\Cubes\FogBugz\FogBugz\FogBugz_2014\FogBugz_2014\bin\";  // this is where the .xmla and .asdatabase files are created

            string DEPLOYMENTWIZARD = @"C:\Program Files (x86)\Microsoft SQL Server\120\Tools\Binn\ManagementStudio\Microsoft.AnalysisServices.Deployment.exe";
            string asdatabaseFILE = BIN + "FogBugz_2014.asdatabase";
            string xmlaFILE = BIN + "FogBugz_2014_Script.xmla"; // this was initially manually created
            Process cmd = new Process();
            cmd.StartInfo.FileName = "cmd.exe";
            cmd.StartInfo.RedirectStandardInput = true;
            cmd.StartInfo.RedirectStandardOutput = true;
            cmd.StartInfo.CreateNoWindow = true;
            cmd.StartInfo.UseShellExecute = false;
            cmd.Start();

            //string cmdText = @"""C:\Program Files (x86)\Microsoft Visual Studio 14.0\Common7\IDE\devenv.exe"" ""C:\Cubes\FogBugz\FogBugz\FogBugz_2014\FogBugz_2014.sln"" /Build Development /Project FogBugz_2014";
            string createASDATABASE = "\"" + DEVENV + "\" \"" + SOLUTION + "\" /Build Development /Project " + PROJECTNAME;
            Debug.WriteLine("createASDATABASE string:");
            Debug.WriteLine(createASDATABASE);
            //string createXMLA = @"""C:\Program Files (x86)\Microsoft SQL Server\120\Tools\Binn\ManagementStudio\Microsoft.AnalysisServices.Deployment.exe"" ""BIN\FogBugz_2014.asdatabase"" /d /o:""BIN\FogBugz_2014_Script.xmla""";
            string createXMLA = "\"" + DEPLOYMENTWIZARD + "\" \"" + asdatabaseFILE + "\" /d /o:\"" + xmlaFILE + "\"";
            Debug.WriteLine("createXMLA string:");
            Debug.WriteLine(createXMLA);

            cmd.StandardInput.WriteLine(createASDATABASE);
            cmd.StandardInput.WriteLine(createXMLA);
            cmd.StandardInput.Flush();
            cmd.StandardInput.Close();
            cmd.WaitForExit();
            Console.WriteLine(cmd.StandardOutput.ReadToEnd());
        }
    }
}
