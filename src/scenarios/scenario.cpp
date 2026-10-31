#include "scenarios/scenario.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <set>
namespace driving {
void Scenario::validate() const {
 const double values[]={ego_speed,target_speed,gap,lead_speed,brake_time,lead_brake,ped_x,ped_y,ped_speed,visible_time,adj_x,adj_speed,dt,duration,lane_width,destination};
 for(double v:values) if(!std::isfinite(v)) throw std::runtime_error("Nonfinite scenario value");
 if(id<0 || kind<0 || kind>7 || ego_speed<0 || ego_speed>40 || target_speed<=0 || target_speed>40 || lead_speed<0 || lead_speed>40 || gap<2 || lead_brake>0 || lead_brake< -10 || brake_time<0 || ped_speed<0 || ped_speed>4 || ped_x<5 || visible_time<0 || adj_speed<0 || adj_speed>45 || dt<.01 || dt>.1 || duration<1 || duration>120 || lane_width<3 || lane_width>5 || destination<=0 || std::abs(adj_x)<5)
 throw std::runtime_error("Invalid scenario physical bounds");
}
std::vector<Scenario> read_scenarios(const std::filesystem::path& path) {
 std::ifstream in(path); if(!in) throw std::runtime_error("Cannot open scenarios: "+path.string());
 std::string line; std::getline(in,line);
 if(!line.empty() && line.back()=='\r') line.pop_back();
 if(line!="id,kind,seed,ego_speed,target_speed,gap,lead_speed,brake_time,lead_brake,ped_x,ped_y,ped_speed,visible_time,adj_x,adj_speed,dt,duration,lane_width,destination") throw std::runtime_error("Scenario CSV schema mismatch");
 std::vector<Scenario> result; std::set<int> ids;
 while(std::getline(in,line)) {
  if(line.empty()) continue;
  for(char& c:line) if(c==',') c=' ';
  std::istringstream row(line); Scenario s;
  if(!(row>>s.id>>s.kind>>s.seed>>s.ego_speed>>s.target_speed>>s.gap>>s.lead_speed>>s.brake_time>>s.lead_brake>>s.ped_x>>s.ped_y>>s.ped_speed>>s.visible_time>>s.adj_x>>s.adj_speed>>s.dt>>s.duration>>s.lane_width>>s.destination)) throw std::runtime_error("Malformed scenario CSV row");
  std::string extra; if(row>>extra) throw std::runtime_error("Extra scenario columns");
  s.validate(); if(!ids.insert(s.id).second) throw std::runtime_error("Duplicate scenario ID"); result.push_back(s);
 }
 if(result.empty()) throw std::runtime_error("Empty scenario dataset");
 return result;
}
}