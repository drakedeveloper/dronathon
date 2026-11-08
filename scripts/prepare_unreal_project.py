"""Prepare an original Unreal project with a checksummed upstream AirSim plugin.

The shipped plugin binary targets5.8.2. Rebuild its source against our installed
5.8.1 engine before launching; never patch module build IDs to force binary use.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
archive=Path(sys.argv[1]).resolve()
expected='4d7cb22241071c0581a33eaf0b9af68f51e222e89092815bbc3cc8f37d8ecffb'
checksum=hashlib.sha256()
with archive.open('rb') as handle:
    for block in iter(lambda:handle.read(8*1024**2),b''):checksum.update(block)
if checksum.hexdigest()!=expected:raise ValueError('Plugin SHA256 does not match upstream release')
project=ROOT/'runtime/unreal/SKYFORGE';plugin=project/'Plugins/AirSim'
with zipfile.ZipFile(archive) as z:
    descriptors=[name for name in z.namelist() if name.endswith('AirSim.uplugin')]
    if len(descriptors)!=1:raise ValueError('Expected one AirSim plugin descriptor')
    prefix=descriptors[0][:-len('AirSim.uplugin')]
    entries=[item for item in z.infolist() if item.filename.startswith(prefix) and not item.is_dir()]
    required=sum(item.file_size for item in entries)
    if shutil.disk_usage(ROOT).free<required+3*1024**3:raise OSError('Need plugin expansion plus3GiB build reserve on D:')
    for item in entries:
        relative=item.filename[len(prefix):]
        target=(plugin/relative).resolve()
        if not target.is_relative_to(plugin.resolve()):raise ValueError('Unsafe archive path')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists() or target.stat().st_size!=item.file_size:
            with z.open(item) as source,target.open('wb') as destination:shutil.copyfileobj(source,destination)

uproject={'FileVersion':3,'EngineAssociation':'5.8','Category':'Simulation',
          'Description':'SKYFORGE original coastal humanitarian rescue simulation',
          'Modules':[{'Name':'SKYFORGE','Type':'Runtime','LoadingPhase':'Default'}],
          'Plugins':[{'Name':'AirSim','Enabled':True},{'Name':'PythonScriptPlugin','Enabled':True},
                     {'Name':'EditorScriptingUtilities','Enabled':True}]}
(project/'SKYFORGE.uproject').write_text(json.dumps(uproject,indent=2))
source=project/'Source/SKYFORGE';source.mkdir(parents=True,exist_ok=True)
(source/'SKYFORGE.Build.cs').write_text('''using UnrealBuildTool;
public class SKYFORGE : ModuleRules {
 public SKYFORGE(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
 }
}
''')
(source/'SKYFORGE.cpp').write_text('''#include "Modules/ModuleManager.h"
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, SKYFORGE, "SKYFORGE");
''')
for name,kind in [('SKYFORGE','Game'),('SKYFORGEEditor','Editor')]:
    (project/'Source'/f'{name}.Target.cs').write_text('''using UnrealBuildTool;
public class NAME : TargetRules {
 public NAME(TargetInfo Target) : base(Target) {
  Type = TargetType.KIND;
  DefaultBuildSettings = BuildSettingsVersion.Latest;
  IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
  ExtraModuleNames.Add("SKYFORGE");
 }
}
'''.replace('NAME',name+'Target').replace('KIND',kind))
config=project/'Config';config.mkdir(exist_ok=True)
(config/'DefaultEngine.ini').write_text('''[/Script/EngineSettings.GameMapsSettings]
EditorStartupMap=/Engine/Maps/Entry
GameDefaultMap=/Engine/Maps/Entry
GlobalDefaultGameMode=/Script/AirSim.AirSimGameMode

[/Script/Engine.RendererSettings]
r.DynamicGlobalIlluminationMethod=0
r.ReflectionMethod=0
r.Shadow.Virtual.Enable=0
r.DefaultFeature.MotionBlur=False
r.AntiAliasingMethod=2
r.TextureStreaming=True

[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX11
''')
(config/'DefaultGame.ini').write_text('''[/Script/EngineSettings.GeneralProjectSettings]
ProjectName=SKYFORGE
ProjectVersion=0.1.0
Description=Autonomous humanitarian coastal rescue research simulator
''')
manifest={'upstream':'https://github.com/Cosys-Lab/Cosys-AirSim/releases/tag/5.8-v3.5.0',
          'sha256':expected,'archive_uncompressed_bytes':required,'shipped_engine':'5.8.2',
          'installed_engine':'5.8.1','required_next_step':'Rebuild plugin and project source against installed engine'}
(project/'plugin-provenance.json').write_text(json.dumps(manifest,indent=2))
print(f'Prepared {project}; plugin expanded {required/1024**3:.2f}GiB. Source rebuild required.',flush=True)
