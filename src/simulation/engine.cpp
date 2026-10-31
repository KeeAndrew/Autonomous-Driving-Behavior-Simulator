#include "simulation/engine.hpp"
#include "metrics/metrics.hpp"
#include <algorithm>
#include <stdexcept>
namespace driving {
void integrate(Vehicle& v,Action action,double dt,double lane_width) {
 if(dt<=0 || !std::isfinite(action.acceleration) || action.lane<0 || action.lane>1) throw std::runtime_error("Invalid dynamics input");
 const double old_a=v.acceleration;
 v.acceleration=std::clamp(std::clamp(action.acceleration,-8.,2.5),old_a-10*dt,old_a+10*dt);
 const double old_v=v.speed;
 v.speed=std::clamp(old_v+v.acceleration*dt,0.,40.);
 v.x+=(old_v+v.speed)*.5*dt;
 // Acceleration records actual speed change, including stop/speed saturation.
 v.acceleration=(v.speed-old_v)/dt;
 const double target=static_cast<double>(action.lane)*lane_width;
 const double requested=std::clamp(1.5*(target-v.y)-2.5*v.lateral_speed,-1.5,1.5);
 const double old_lat_a=v.lateral_acceleration;
 v.lateral_acceleration=std::clamp(requested,old_lat_a-3*dt,old_lat_a+3*dt);
 const double old_lat_v=v.lateral_speed;
 v.lateral_speed=std::clamp(v.lateral_speed+v.lateral_acceleration*dt,-1.2,1.2);
 if(v.speed<.1) { v.lateral_speed=0; v.lateral_acceleration=0; }
 v.y=std::clamp(v.y+(old_lat_v+v.lateral_speed)*.5*dt,-.5,lane_width+.5);
 v.heading=std::atan2(v.lateral_speed,std::max(v.speed,.01));
}
double separation(const Vehicle& e,const Actor& a) {
 const double dx=std::max(0.,std::abs(e.x-a.x)-(4.5+a.length)*.5);
 const double dy=std::max(0.,std::abs(e.y-a.y)-(1.8+a.width)*.5);
 return std::hypot(dx,dy);
}
bool overlaps(const Vehicle& e,const Actor& a) { return std::abs(e.x-a.x)<=(4.5+a.length)*.5 && std::abs(e.y-a.y)<=(1.8+a.width)*.5; }
bool swept_collision(const Vehicle& before,const Vehicle& after,const Actor& a0,const Actor& a1) {
 double lo=0,hi=1;
 const double p[]={before.x-a0.x,before.y-a0.y};
 const double d[]={after.x-a1.x-p[0],after.y-a1.y-p[1]};
 const double half[]={(4.5+a0.length)*.5,(1.8+a0.width)*.5};
 for(int axis=0;axis<2;++axis) {
  if(std::abs(d[axis])<1e-12) { if(std::abs(p[axis])>half[axis]) return false; }
  else { double t0=(-half[axis]-p[axis])/d[axis],t1=(half[axis]-p[axis])/d[axis]; if(t0>t1) std::swap(t0,t1); lo=std::max(lo,t0); hi=std::min(hi,t1); if(lo>hi) return false; }
 }
 return true;
}
static Observation observe(const Scenario& s,const Vehicle& e,const Actor& lead,const Actor& adj,const Actor& ped,double time) {
 Observation o; o.speed=e.speed; o.target=s.target_speed; o.lead_speed=e.speed; o.acceleration=e.acceleration;
 o.lane=std::abs(e.y-s.lane_width)<.15 ? 1:0;
 for(const Actor* a:{&lead,&adj}) {
  if(s.kind==3 && a==&lead && time<s.visible_time) continue;
  const double gap=a->x-e.x-(a->length+4.5)*.5;
  if(std::abs(a->y-e.y)<(a->width+1.8)*.5+.15 && a->x>e.x && gap<o.gap) { o.gap=gap; o.lead_speed=a->speed; }
 }
 o.closing=o.speed-o.lead_speed; o.ttc=ttc(o.gap,o.closing);
 if((s.kind==4 || s.kind==5) && time>=s.visible_time && ped.x>e.x && ped.y< s.lane_width+1.5) {
  o.ped_gap=ped.x-e.x-2.55;
  o.ped_eta=ped.y<e.y-1.2 ? (e.y-1.2-ped.y)/std::max(s.ped_speed,.01):0;
  if(ped.y>e.y+1.2) o.ped_eta=20;
 }
 const double other_y=o.lane==0 ? s.lane_width:0;
 for(const Actor* a:{&lead,&adj}) if(std::abs(a->y-other_y)<1.) {
  const double delta=a->x-e.x;
  if(delta>=0) o.adj_front=std::min(o.adj_front,delta-4.5);
  else { o.adj_rear=std::min(o.adj_rear,-delta-4.5); o.adj_closing=a->speed-e.speed; }
 }
 o.lane_safe=safe_lane_change(o.adj_front,o.adj_rear,o.adj_closing,o.speed);
 return o;
}
Metrics simulate(const Scenario& s,Controller controller,const std::function<void(const Frame&)>& sink) {
 s.validate(); Vehicle ego; ego.speed=s.ego_speed;
 Actor lead{s.gap+4.5,0,s.lead_speed,4.5,1.8},adj{s.adj_x,s.lane_width,s.adj_speed,4.5,1.8};
 Actor ped{s.ped_x,(s.kind==4 || s.kind==5)?s.ped_y:-100.,s.ped_speed,.6,.6};
 Accumulator metrics(s);
 const int count=static_cast<int>(std::ceil(s.duration/s.dt));
 for(int step=0;step<count;++step) {
  const double time=static_cast<double>(step)*s.dt,dt=std::min(s.dt,s.duration-time);
  Observation o=observe(s,ego,lead,adj,ped,time); Action action=controller.decide(o);
  const Vehicle before=ego; const Actor lead0=lead,adj0=adj,ped0=ped;
  integrate(ego,action,dt,s.lane_width);
  double lead_a=0;
  if(time>=s.brake_time && (s.kind==1 || s.kind==2)) lead_a=(s.kind==2 && time>=s.brake_time+3)?2.:s.lead_brake;
  const double old_speed=lead.speed; lead.speed=std::max(0.,lead.speed+lead_a*dt); lead.x+=(old_speed+lead.speed)*.5*dt;
  adj.x+=adj.speed*dt;
  if(s.kind==4 || s.kind==5) ped.y+=s.ped_speed*dt;
  Frame f; f.time=time+dt; f.ego=ego; f.lead=lead; f.adjacent=adj; f.pedestrian=ped; f.observation=o; f.action=action;
  const auto current=observe(s,ego,lead,adj,ped,time+dt); f.gap=current.gap; f.ttc=current.ttc;
  f.separation=std::min({separation(ego,lead),separation(ego,adj),separation(ego,ped)});
  f.collision=swept_collision(before,ego,lead0,lead) || swept_collision(before,ego,adj0,adj) || swept_collision(before,ego,ped0,ped);
  f.jerk=(ego.acceleration-before.acceleration)/dt; f.lateral_jerk=(ego.lateral_acceleration-before.lateral_acceleration)/dt;
  metrics.update(f,dt); if(sink) sink(f);
  if(f.collision || ego.x>=s.destination) break;
 }
 return metrics.finish(s.destination);
}
}