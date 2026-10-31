#include "metrics/metrics.hpp"
#include "controllers/controllers.hpp"
#include <algorithm>
#include <cmath>
namespace driving {
Accumulator::Accumulator(const Scenario& s) { m_.id=s.id; m_.kind=s.kind; lane_width_=s.lane_width; }
void Accumulator::update(const Frame& f,double dt) {
 ++m_.steps; m_.elapsed=f.time; m_.distance=f.ego.x;
 m_.collision=std::max(m_.collision,static_cast<int>(f.collision));
 m_.min_following_gap=std::min(m_.min_following_gap,f.gap); m_.min_separation=std::min(m_.min_separation,f.separation); m_.min_ttc=std::min(m_.min_ttc,f.ttc);
 const bool hard=f.ego.acceleration< -4.; if(hard && !braking_) ++m_.hard_brakes; braking_=hard;
 const bool near=!f.collision && (f.separation<1. || f.ttc<1.5); if(near && !near_) ++m_.near_misses; near_=near;
 m_.peak_deceleration=std::max(m_.peak_deceleration,-f.ego.acceleration);
 if(f.ego.acceleration< -.1) m_.braking_time+=dt;
 if(f.observation.lane==0 && std::abs(f.ego.y-lane_width_)<.15) ++m_.lane_changes;
 sum_a_+=f.ego.acceleration*dt; sum_a2_+=f.ego.acceleration*f.ego.acceleration*dt;
 sum_j2_+=f.jerk*f.jerk*dt; sum_lj2_+=f.lateral_jerk*f.lateral_jerk*dt;
}
Metrics Accumulator::finish(double destination) {
 m_.completed=static_cast<int>(!m_.collision && m_.distance>=destination);
 if(m_.completed) m_.arrival=m_.elapsed;
 m_.progress=std::min(1.,m_.distance/destination); m_.average_speed=m_.distance/m_.elapsed;
 m_.rms_jerk=std::sqrt(sum_j2_/m_.elapsed); m_.rms_lateral_jerk=std::sqrt(sum_lj2_/m_.elapsed);
 m_.acceleration_variance=std::max(0.,sum_a2_/m_.elapsed-std::pow(sum_a_/m_.elapsed,2));
 m_.hard_brakes_per_km=m_.distance>0 ? m_.hard_brakes*1000./m_.distance:infinity;
 return m_;
}
void metrics_header(std::ostream& o) { o<<"id,kind,controller,collision,near_misses,min_separation,min_following_gap,min_ttc,distance,elapsed,arrival,average_speed,completed,progress,hard_brakes,hard_brakes_per_km,peak_deceleration,braking_time,rms_jerk,acceleration_variance,rms_lateral_jerk,lane_changes\n"; }
void write_metrics(std::ostream& o,const Metrics& m,const std::string& c) {
 o<<m.id<<','<<m.kind<<','<<c<<','<<m.collision<<','<<m.near_misses<<','<<m.min_separation<<','<<m.min_following_gap<<','<<m.min_ttc<<','<<m.distance<<','<<m.elapsed<<','<<m.arrival<<','<<m.average_speed<<','<<m.completed<<','<<m.progress<<','<<m.hard_brakes<<','<<m.hard_brakes_per_km<<','<<m.peak_deceleration<<','<<m.braking_time<<','<<m.rms_jerk<<','<<m.acceleration_variance<<','<<m.rms_lateral_jerk<<','<<m.lane_changes<<'\n';
}
void telemetry_header(std::ostream& o) {
 o<<"id,controller,time,x,y,speed,acceleration,jerk,lateral_jerk,heading,lead_x,lead_y,adj_x,adj_y,ped_x,ped_y,gap,ttc,separation,collision,command,lane,obs_speed,target,obs_gap,lead_speed,closing,obs_ttc,ped_gap,ped_eta,adj_front,adj_rear,adj_closing,obs_acceleration,label\n";
}
void write_frame(std::ostream& o,int id,const std::string& c,const Frame& f) {
 o<<id<<','<<c<<','<<f.time<<','<<f.ego.x<<','<<f.ego.y<<','<<f.ego.speed<<','<<f.ego.acceleration<<','<<f.jerk<<','<<f.lateral_jerk<<','<<f.ego.heading<<','<<f.lead.x<<','<<f.lead.y<<','<<f.adjacent.x<<','<<f.adjacent.y<<','<<f.pedestrian.x<<','<<f.pedestrian.y<<','<<f.gap<<','<<f.ttc<<','<<f.separation<<','<<f.collision<<','<<f.action.acceleration<<','<<f.action.lane;
 for(double x:f.observation.features()) o<<','<<x;
 o<<','<<teacher(f.observation).acceleration<<'\n';
}
}