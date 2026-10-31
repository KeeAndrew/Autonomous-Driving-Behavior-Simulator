#pragma once
#include "simulation/types.hpp"
#include <filesystem>
namespace driving {
double ttc(double clearance,double closing_speed);
bool safe_lane_change(double front,double rear,double closing,double speed);
Action baseline(const Observation& o);
Action teacher(const Observation& o);
Action hybrid(const Observation& o);
struct Node { int left=-1,right=-1,feature=-1; double threshold=0,value=0; };
class Forest {
 std::vector<std::vector<Node>> trees_;
public:
 void load(const std::filesystem::path& path);
 double predict(const Features& features) const;
 bool empty() const { return trees_.empty(); }
};
class Controller {
 std::string mode_; const Forest* forest_; int desired_lane_=0; bool changing_=false;
public:
 Controller(std::string mode,const Forest* forest=nullptr);
 Action decide(const Observation& o);
};
}