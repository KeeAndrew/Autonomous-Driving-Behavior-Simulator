#pragma once
#include "simulation/types.hpp"
#include <ostream>
namespace driving {
class Accumulator {
 Metrics m_; double lane_width_=3.6; bool braking_=false,near_=false; double sum_a_=0,sum_a2_=0,sum_j2_=0,sum_lj2_=0;
public:
 explicit Accumulator(const Scenario& s);
 void update(const Frame& f,double dt);
 Metrics finish(double destination);
};
void metrics_header(std::ostream& out);
void write_metrics(std::ostream& out,const Metrics& m,const std::string& controller);
void telemetry_header(std::ostream& out);
void write_frame(std::ostream& out,int id,const std::string& controller,const Frame& f);
}