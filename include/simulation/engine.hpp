#pragma once
#include "controllers/controllers.hpp"
#include <functional>
namespace driving {
void integrate(Vehicle& v,Action a,double dt,double lane_width);
double separation(const Vehicle& ego,const Actor& actor);
bool swept_collision(const Vehicle& before,const Vehicle& after,const Actor& actor_before,const Actor& actor_after);
bool overlaps(const Vehicle& ego,const Actor& actor);
Metrics simulate(const Scenario& s,Controller controller,const std::function<void(const Frame&)>& sink={});
}