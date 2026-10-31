import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.neighbors import NearestNeighbors
from threadpoolctl import threadpool_limits
from python.analysis.divergence import CLUSTER_FEATURES
from python.common import save_json, KINDS

def clustering_input(df):
    if len(df)<3 or df.id.duplicated().any(): raise ValueError('Need >=3 unique divergence records')
    if not set(CLUSTER_FEATURES).issubset(df): raise ValueError('Missing clustering features')
    x=df[CLUSTER_FEATURES].to_numpy(float)
    if not np.isfinite(x).all(): raise ValueError('Nonfinite clustering data')
    if len(np.unique(x,axis=0))<3: raise ValueError('Need >=3 distinct feature vectors')
    return StandardScaler().fit_transform(x)

def silhouette(x,labels):
    unique=np.unique(labels)
    if len(unique)<2 or len(unique)>=len(x): return None
    # deterministic stratified-enough bounded sample; catch all-one-cluster sample
    try: return float(silhouette_score(x,labels,sample_size=min(1500,len(x)),random_state=51))
    except ValueError: return None

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True); df=pd.read_csv(a.input)
    if len(df)<3 or len(df[CLUSTER_FEATURES].drop_duplicates())<3:
        save_json(a.out/'clustering.json',{'records':len(df),'status':'insufficient distinct divergences; no clusters fabricated'}); return
    x=clustering_input(df); candidates=[]; models=[]
    # Avoid high thread-count overhead and keep reproducibility on small matrices.
    with threadpool_limits(limits=1):
        for k in range(2,min(8,len(np.unique(x,axis=0))-1)+1):
            km=KMeans(n_clusters=k,n_init=10,random_state=51).fit(x)
            candidates.append({'k':k,'inertia':float(km.inertia_),'silhouette':silhouette(x,km.labels_)})
            models.append(km)
    best=max(range(len(models)),key=lambda i:candidates[i]['silhouette'] if candidates[i]['silhouette'] is not None else -2)
    labels=models[best].labels_; df['kmeans']=labels
    min_samples=max(5,2*x.shape[1]); min_samples=min(min_samples,len(x))
    distances=NearestNeighbors(n_neighbors=min_samples).fit(x).kneighbors(x)[0][:,-1]
    eps_values=np.unique(np.maximum(.05,np.quantile(distances,[.5,.7,.85,.95])))
    db_candidates=[]; db_labels=[]
    for eps in eps_values:
        l=DBSCAN(eps=float(eps),min_samples=min_samples).fit_predict(x)
        valid=l>=0; score=silhouette(x[valid],l[valid]) if valid.sum()>2 else None
        db_candidates.append({'eps':float(eps),'min_samples':min_samples,'noise_fraction':float(np.mean(~valid)),
                              'clusters':len(set(l)-{-1}),'silhouette_without_noise':score})
        db_labels.append(l)
    db_best=max(range(len(db_candidates)),key=lambda i:db_candidates[i]['silhouette_without_noise'] if db_candidates[i]['silhouette_without_noise'] is not None else -2)
    df['dbscan']=db_labels[db_best]; df['category']=df.kind.map(dict(enumerate(KINDS)))
    df.to_csv(a.out/'cluster_assignments.csv',index=False)
    df.groupby('kmeans')[CLUSTER_FEATURES].mean().to_csv(a.out/'cluster_profiles.csv')
    pd.crosstab(df.kmeans,df.category,normalize='index').to_csv(a.out/'cluster_categories.csv')
    projection=PCA(n_components=2,random_state=51).fit_transform(x)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax,col in zip(axes,['kmeans','dbscan']):
        plot=ax.scatter(*projection.T,c=df[col],s=5,cmap='tab10',alpha=.6); ax.set(title=col,xlabel='PC1',ylabel='PC2'); fig.colorbar(plot,ax=ax)
    fig.tight_layout(); fig.savefig(a.out/'clusters.png',dpi=160); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    axes[0].plot([c['k'] for c in candidates],[c['inertia'] for c in candidates],'o-'); axes[0].set(title='Elbow',xlabel='k',ylabel='Inertia')
    axes[1].plot([c['k'] for c in candidates],[c['silhouette'] for c in candidates],'o-'); axes[1].set(title='Silhouette',xlabel='k')
    axes[2].plot(np.sort(distances)); axes[2].set(title=f'{min_samples}-neighbor distances',xlabel='Sorted point',ylabel='Distance')
    fig.tight_layout(); fig.savefig(a.out/'selection.png',dpi=160); plt.close(fig)
    save_json(a.out/'clustering.json',{'records':len(df),'features':CLUSTER_FEATURES,'scaling':'StandardScaler',
        'kmeans_candidates':candidates,'selected_k':candidates[best]['k'],'dbscan_candidates':db_candidates,
        'selected_dbscan':db_candidates[db_best],'adjusted_rand_including_noise':float(adjusted_rand_score(labels,df.dbscan))})
    lines=['# Behavioral divergence clusters','',f'Analyzed {len(df)} unique scenario records. Clusters are statistical groups, not predetermined scenario classes.','']
    for label,group in df.groupby('kmeans'):
        cats=group.category.value_counts(normalize=True).head(2)
        lines.append(f'- Cluster {label}: {len(group)} records; mean acceleration disagreement {group.command_rms.mean():.2f} m/s²; mean trajectory disagreement {group.trajectory_rms.mean():.2f} m; most common categories: '+', '.join(f'{k} ({v:.0%})' for k,v in cats.items())+'.')
    lines.extend(['',f'DBSCAN selected {db_candidates[db_best]["clusters"]} groups; noise fraction {db_candidates[db_best]["noise_fraction"]:.1%}.',
        'Selection uses the largest non-noise silhouette among the predeclared nearest-neighbor quantiles. Noise is retained as -1. Neither cluster count nor eps is chosen to match semantic labels.'])
    (a.out/'findings.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'Clustered {len(df)} divergences; selected k={candidates[best]["k"]}')
if __name__=='__main__': main()