#pragma once
#include <array>
#include <cmath>
#include <limits>
#include <string>
#include <vector>
namespace driving {
constexpr double infinity = std::numeric_limits<double>::infinity();
constexpr int feature_count = 12;
using Features = std::array<double, feature_count>;
struct Vehicle { double x=0,y=0,speed=0,acceleration=0,lateral_speed=0,lateral_acceleration=0,heading=0; };
struct Actor { double x=0,y=0,speed=0,length=4.5,width=1.8; };
struct Scenario {
 int id=0,kind=0; unsigned seed=0;
 double ego_speed=18,target_speed=22,gap=35,lead_speed=14,brake_time=4,lead_brake=-4;
 double ped_x=55,ped_y=-6,ped_speed=1.5,visible_time=0,adj_x=-25,adj_speed=20;
 double dt=.05,duration=15,lane_width=3.6,destination=200;
 void validate() const;
};
struct Observation {
 double speed=0,target=0,gap=250,lead_speed=0,closing=0,ttc=infinity;
 double ped_gap=250,ped_eta=20,adj_front=250,adj_rear=250,adj_closing=0,acceleration=0;
 int lane=0; bool lane_safe=false;
 Features features() const;
};
struct Action { double acceleration=0; int lane=0; };
struct Frame {
 double time=0; Vehicle ego; Actor lead,adjacent,pedestrian;
 Observation observation; Action action; double gap=250,ttc=infinity,separation=250,jerk=0,lateral_jerk=0;
 bool collision=false;
};
struct Metrics {
 int id=0,kind=0,collision=0,near_misses=0,hard_brakes=0,lane_changes=0,completed=0,steps=0;
 double min_separation=250,min_following_gap=250,min_ttc=infinity,distance=0,elapsed=0,arrival=infinity,average_speed=0,progress=0;
 double peak_deceleration=0,braking_time=0,rms_jerk=0,acceleration_variance=0,rms_lateral_jerk=0,hard_brakes_per_km=0;
};
}