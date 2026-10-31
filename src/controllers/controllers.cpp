#include "controllers/controllers.hpp"
#include <algorithm>
#include <fstream>
#include <stdexcept>
namespace driving {
double ttc(double clearance,double closing_speed) { return clearance<=0 ? 0 : (closing_speed>1e-6 ? clearance/closing_speed : infinity); }
bool safe_lane_change(double front,double rear,double closing,double speed) {
 return front>std::max(15.,1.4*speed) && rear>std::max(12.,2.5*std::max(0.,closing));
}
Features Observation::features() const {
 return {speed,target,std::clamp(gap,0.,250.),lead_speed,closing,std::min(ttc,30.),std::clamp(ped_gap,0.,250.),std::clamp(ped_eta,0.,20.),adj_front,adj_rear,adj_closing,acceleration};
}
Action baseline(const Observation& o) {
 double a=std::clamp(.7*(o.target-o.speed),-4.,2.5);
 if(o.gap<3+1.25*o.speed) a=std::min(a,.45*(o.gap-3-1.25*o.speed)-.8*o.closing);
 if(o.gap<5) a=-8;
 if(o.ped_gap<6+o.speed*o.speed/8 && o.ped_eta<3) a=std::min(a,-5.);
 int lane=o.lane;
 if(o.lane==0 && o.gap<45 && o.closing>2 && o.lane_safe && o.ped_gap>100) lane=1;
 return {std::clamp(a,-8.,2.5),lane};
}
Action teacher(const Observation& o) {
 // IDM-inspired demonstrator: observable state only, with stopping clearance.
 const double dynamic=std::max(0.,1.6*o.speed+o.speed*o.closing/(2*std::sqrt(2.*3.)));
 double a=2.*(1-std::pow(o.speed/std::max(o.target,1.),4)-std::pow((3+dynamic)/std::max(o.gap,.5),2));
 if(o.ttc<2.5) a=std::min(a,-o.closing*o.closing/(2*std::max(o.gap-2.,.5)));
 if(o.ped_eta<3.5 && o.ped_gap<o.speed*o.speed/6+8) a=std::min(a,-o.speed*o.speed/(2*std::max(o.ped_gap-3,.5)));
 int lane=o.lane;
 if(o.lane==0 && o.gap<55 && o.closing>1.5 && o.lane_safe && o.ped_gap>100) lane=1;
 return {std::clamp(a,-8.,2.5),lane};
}
Action hybrid(const Observation& o) {
 Action a=baseline(o);
 const double desired=3+1.6*o.speed+std::max(0.,o.speed*o.closing/(2*std::sqrt(6.)));
 a.acceleration=std::min(a.acceleration,std::clamp(.25*(o.gap-desired)-.65*o.closing,-8.,2.5));
 if(o.ttc<3. && o.closing>0) a.acceleration=std::min(a.acceleration,-o.closing*o.closing/(2*std::max(o.gap-3.,.5)));
 if(o.ped_eta<3.5 && o.ped_gap<8+o.speed*o.speed/6) a.acceleration=std::min(a.acceleration,-o.speed*o.speed/(2*std::max(o.ped_gap-3.,.5)));
 return {std::clamp(a.acceleration,-8.,2.5),a.lane};
}
void Forest::load(const std::filesystem::path& path) {
 std::ifstream in(path); if(!in) throw std::runtime_error("Cannot open forest");
 std::string magic; int version=0,features=0,count=0;
 if(!(in>>magic>>version>>features>>count) || magic!="DRIVING_FOREST" || version!=1 || features!=feature_count || count<1 || count>1024) throw std::runtime_error("Invalid forest header");
 std::vector<std::vector<Node>> trees;
 for(int i=0;i<count;++i) {
  int n=0; if(!(in>>n) || n<1 || n>100000) throw std::runtime_error("Invalid node count");
  std::vector<Node> nodes(static_cast<std::size_t>(n));
  for(int j=0;j<n;++j) {
   auto& v=nodes[static_cast<std::size_t>(j)];
   if(!(in>>v.left>>v.right>>v.feature>>v.threshold>>v.value) || !std::isfinite(v.threshold) || !std::isfinite(v.value)) throw std::runtime_error("Invalid forest node");
   if(v.left==-1) { if(v.right!=-1 || v.feature!=-2) throw std::runtime_error("Invalid leaf"); }
   else if(v.left<=j || v.right<=j || v.left>=n || v.right>=n || v.feature<0 || v.feature>=feature_count) throw std::runtime_error("Invalid tree topology");
  }
  trees.push_back(std::move(nodes));
 }
 std::string extra; if(in>>extra) throw std::runtime_error("Extra model data");
 trees_=std::move(trees);
}
double Forest::predict(const Features& f) const {
 if(empty()) throw std::runtime_error("Forest not loaded");
 for(double x:f) if(!std::isfinite(x)) throw std::runtime_error("Nonfinite model feature");
 double sum=0;
 for(const auto& tree:trees_) {
  std::size_t i=0;
  // sklearn casts inputs to float32 before applying double thresholds.
  while(tree[i].left!=-1) { const auto& n=tree[i]; i=static_cast<std::size_t>(static_cast<float>(f[static_cast<std::size_t>(n.feature)])<=n.threshold ? n.left:n.right); }
  sum+=tree[i].value;
 }
 return sum/static_cast<double>(trees_.size());
}
Controller::Controller(std::string mode,const Forest* forest):mode_(std::move(mode)),forest_(forest) {
 if(mode_!="baseline" && mode_!="teacher" && mode_!="hybrid" && mode_!="ml") throw std::runtime_error("Unknown controller");
 if(mode_=="ml" && (!forest_ || forest_->empty())) throw std::runtime_error("ML requires valid model; refusing silent baseline evaluation");
}
Action Controller::decide(const Observation& o) {
 Action a= mode_=="teacher" ? teacher(o) : (mode_=="hybrid" ? hybrid(o) : baseline(o));
 if(mode_=="ml") { try { a.acceleration=std::clamp(forest_->predict(o.features()),-8.,2.5); } catch(const std::exception&) { a=baseline(o); } }
 // Commit to a lane change once started; prevent switching midway through traffic.
 if(!changing_ && a.lane!=o.lane && o.lane_safe) { desired_lane_=a.lane; changing_=true; }
 if(changing_ && o.lane==desired_lane_) changing_=false;
 a.lane=changing_ ? desired_lane_:o.lane;
 return a;
}
}