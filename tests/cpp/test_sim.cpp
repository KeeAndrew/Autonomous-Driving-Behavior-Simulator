#include "simulation/engine.hpp"
#include "scenarios/scenario.hpp"
#include "metrics/metrics.hpp"
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace driving;
static int checks=0;
static void require(bool condition,const char* message) { ++checks; if(!condition) throw std::runtime_error(message); }
int main() {
 try {
  require(std::isinf(ttc(20,0)),"zero closing TTC");
  require(std::isinf(ttc(20,-5)),"receding TTC");
  require(std::abs(ttc(20,5)-4)<1e-12,"closing TTC");
  require(ttc(-1,5)==0,"overlap TTC");
  Vehicle v; v.speed=10; integrate(v,{2.5,0},.05,3.6);
  require(std::abs(v.acceleration-.5)<1e-10,"jerk ramp");
  require(std::abs(v.x-.500625)<1e-10,"trapezoidal integration");
  for(int i=0;i<2000;++i) integrate(v,{100,0},.05,3.6);
  require(v.speed<=40 && v.acceleration<=2.5,"speed and acceleration bounds");
  for(int i=0;i<2000;++i) { integrate(v,{-100,0},.05,3.6); require(v.acceleration>=-8.-1e-10,"braking bound"); }
  require(v.speed==0,"nonnegative speed");
  v={}; Actor a{4.5,0,0,4.5,1.8}; require(overlaps(v,a),"touching collision");
  a.x=4.6; require(!overlaps(v,a) && std::abs(separation(v,a)-.1)<1e-10,"dimension-aware separation");
  a.y=4; require(!overlaps(v,a),"adjacent lane separation");
  Vehicle start{},end{}; end.x=10;
  Actor crossing{5,0,0,.6,.6};
  require(!overlaps(start,crossing) && !overlaps(end,crossing) && swept_collision(start,end,crossing,crossing),"swept fast longitudinal collision");
  Actor ped0{0,-4,0,.6,.6},ped1{0,4,0,.6,.6};
  require(!overlaps(start,ped0) && !overlaps(start,ped1) && swept_collision(start,start,ped0,ped1),"swept pedestrian crossing");
  crossing.x=100; require(!swept_collision(start,end,crossing,crossing),"disjoint swept motion");
  Scenario metric_scenario; metric_scenario.lane_width=4.; Accumulator accumulator(metric_scenario);
  Frame frame; frame.separation=2; frame.ttc=3; frame.gap=8;
  const double accelerations[]={-5,-6,-3,-5},jerks[]={5,1,3,2};
  for(int i=0;i<4;++i) { frame.time=i+1; frame.ego.x=10.*(i+1); frame.ego.acceleration=accelerations[i]; frame.jerk=jerks[i]; frame.gap=i==1?3:8; accumulator.update(frame,1.); }
  const auto exact=accumulator.finish(100.);
  require(exact.hard_brakes==2 && exact.braking_time==4 && exact.peak_deceleration==6,"brake episode metrics");
  require(std::abs(exact.rms_jerk-std::sqrt(39./4))<1e-12 && std::abs(exact.acceleration_variance-1.1875)<1e-12,"time-weighted comfort metrics");
  require(exact.min_following_gap==3 && exact.distance==40 && exact.average_speed==10 && !exact.completed && std::isinf(exact.arrival),"clearance and unsuccessful route metrics");
  require(!safe_lane_change(100,10,15,20),"reject approaching adjacent rear");
  require(!safe_lane_change(10,100,0,20),"reject adjacent front");
  require(safe_lane_change(100,100,1,20),"accept safe gaps");
  Observation o; o.speed=20; o.target=25; o.ped_gap=15; o.ped_eta=.5;
  require(baseline(o).acceleration<0 && teacher(o).acceleration<0 && hybrid(o).acceleration<0,"pedestrian stopping decisions");
  o.ped_gap=250; o.gap=10; o.lead_speed=5; o.closing=15; o.ttc=ttc(10,15);
  require(teacher(o).acceleration<0 && hybrid(o).acceleration<0,"relative velocity braking");
  o.gap=250; o.closing=0; o.lane_safe=true; require(baseline(o).acceleration>0,"free-road acceleration");
  Scenario s; s.kind=1; const auto m1=simulate(s,Controller("baseline")),m2=simulate(s,Controller("baseline"));
  require(m1.distance==m2.distance && m1.collision==m2.collision && m1.rms_jerk==m2.rms_jerk,"deterministic replay");
  s.dt=0; bool rejected=false; try{s.validate();}catch(const std::exception&){rejected=true;} require(rejected,"invalid timestep rejected");
  rejected=false; try{Controller bad("ml");}catch(const std::exception&){rejected=true;} require(rejected,"missing ML model rejected");
  v={}; v.speed=20;
  for(int i=0;i<200;++i) { integrate(v,{0,1},.05,4.); require(v.y>=-.5 && v.y<=4.5 && std::abs(v.lateral_speed)<=1.2,"lane dynamics bounds"); }
  require(std::abs(v.y-4)<.02,"lane target reached");
  const auto file=std::filesystem::temp_directory_path()/"driving_test_model.forest";
  // Keep fixture inside current build directory, not outside the repository.
  const auto local=std::filesystem::current_path()/file.filename();
  {std::ofstream f(local); f<<"DRIVING_FOREST 1 12 1\n3\n1 2 0 10 0\n-1 -1 -2 -2 -1\n-1 -1 -2 -2 2\n";}
  Forest forest; forest.load(local); Features f{}; f[0]=10; require(forest.predict(f)==-1,"tree <= branch"); f[0]=11;require(forest.predict(f)==2,"tree right branch");
  {std::ofstream out(local);out<<"DRIVING_FOREST 1 12 1\n2\n0 1 0 10 0\n-1 -1 -2 -2 0\n";}
  rejected=false;try{forest.load(local);}catch(const std::exception&){rejected=true;}require(rejected,"cyclic model rejected");
  std::filesystem::remove(local);
  std::cout<<"Passed "<<checks<<" contract checks\n";
 } catch(const std::exception& e) {std::cerr<<"FAILED: "<<e.what()<<'\n';return 1;}
 return 0;
}