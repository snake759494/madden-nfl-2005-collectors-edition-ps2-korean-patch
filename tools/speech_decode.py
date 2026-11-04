import os,sys,subprocess,glob
from concurrent.futures import ThreadPoolExecutor
V=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','ext','vgm','vgmstream-cli.exe'))


fs=sorted(glob.glob(os.path.abspath(sys.argv[1])+'/*/*.asf'))
fs=[f for f in fs if not os.path.exists(f+'.wav')]
B=[fs[i:i+200] for i in range(0,len(fs),200)]
B=[[os.path.basename(x) for x in b] for b in B]
dirs=[os.path.dirname(f) for f in fs[::200]]
with ThreadPoolExecutor(4) as ex: list(ex.map(lambda a: subprocess.run([V,'-o','?f.wav']+a[1],capture_output=True,cwd=a[0]),zip(dirs,B)))
