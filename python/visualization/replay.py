import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--telemetry',type=Path,nargs='+',required=True)
    p.add_argument('--id',type=int,required=True)
    p.add_argument('--out',type=Path)
    p.add_argument('--gif',type=Path)
    p.add_argument('--lane-width',type=float,default=3.6)
    a=p.parse_args()
    frames=[]
    for file in a.telemetry:
        df=pd.read_csv(file); df=df[df.id.eq(a.id)]
        if df.empty: raise ValueError(f'Scenario {a.id} missing from {file}')
        frames.append(df)
    fig,axes=plt.subplots(4,1,figsize=(12,10),gridspec_kw={'height_ratios':[2,1,1,1]})
    for df in frames:
        name=df.controller.iloc[0]
        axes[0].plot(df.x,df.y,label=name)
        for ax,col in zip(axes[1:],['speed','acceleration','ttc']): ax.plot(df.time,df[col].replace(np.inf,np.nan).clip(upper=30) if col=='ttc' else df[col],label=name)
    axes[0].axhline(a.lane_width/2,color='gray',ls='--')
    axes[0].set(ylim=(-2,a.lane_width+2),xlabel='Road x (m)',ylabel='Lane y (m)',title=f'Scenario {a.id}: trajectories and current actor positions')
    for ax,col in zip(axes[1:],['Speed (m/s)','Acceleration (m/s²)','TTC (s)']): ax.set(xlabel='Time (s)',ylabel=col)
    axes[3].set_title('TTC display capped at 30 s; nonclosing values omitted',fontsize=10)
    axes[3].set_xlim(0,max(float(df.time.max()) for df in frames))
    if not any(np.isfinite(df.ttc).any() for df in frames):
        axes[3].text(.5,.5,'No finite longitudinal TTC',transform=axes[3].transAxes,ha='center',va='center',color='gray')
    for ax in axes: ax.legend(loc='upper right'); ax.grid(alpha=.2)
    actors=[]
    colors=['tab:blue','tab:orange','tab:green']
    for j,df in enumerate(frames):
        shapes=[Rectangle((0,0),4.5,1.8,color=colors[j%3],alpha=.7),Rectangle((0,0),4.5,1.8,color='gray',alpha=.5),Rectangle((0,0),4.5,1.8,color='purple',alpha=.4),Rectangle((0,0),.6,.6,color='red')]
        for shape in shapes: axes[0].add_patch(shape)
        actors.append(shapes)
    times=np.unique(np.concatenate([df.time.to_numpy() for df in frames]))
    def update(i):
        time=times[i]
        axes[0].set_title(f'Scenario {a.id}: t={time:.2f} s (actors freeze when a rollout ends)')
        for df,shapes in zip(frames,actors):
            idx=max(0,int(np.searchsorted(df.time.to_numpy(),time,side='right'))-1)
            row=df.iloc[min(idx,len(df)-1)]
            for shape,(x,y) in zip(shapes,[(row.x,row.y),(row.lead_x,row.lead_y),(row.adj_x,row.adj_y),(row.ped_x,row.ped_y)]):
                shape.set_xy((x-shape.get_width()/2,y-shape.get_height()/2))
        return [s for group in actors for s in group]
    update(0); fig.tight_layout()
    if a.out: a.out.parent.mkdir(parents=True,exist_ok=True); fig.savefig(a.out,dpi=160)
    animation=None
    if a.gif or not a.out:
        animation=FuncAnimation(fig,update,frames=len(times),interval=100,blit=False)
    if a.gif: a.gif.parent.mkdir(parents=True,exist_ok=True); animation.save(a.gif,writer=PillowWriter(fps=10))
    if not a.out and not a.gif: plt.show()
    else: plt.close(fig)
if __name__=='__main__': main()