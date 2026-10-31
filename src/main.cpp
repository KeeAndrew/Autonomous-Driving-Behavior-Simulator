#include "scenarios/scenario.hpp"
#include "simulation/engine.hpp"
#include "metrics/metrics.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
using namespace driving;
static std::ofstream output(const std::filesystem::path& path) {
 if(path.has_parent_path()) std::filesystem::create_directories(path.parent_path());
 std::ofstream out(path); if(!out) throw std::runtime_error("Cannot write "+path.string()); out<<std::setprecision(17); return out;
}
int main(int argc,char** argv) {
 try {
  std::map<std::string,std::string> args;
  for(int i=1;i<argc;i+=2) { if(i+1>=argc || std::string(argv[i]).rfind("--",0)!=0 || args.contains(argv[i])) throw std::runtime_error("Expected unique --flag value pairs"); args[argv[i]]=argv[i+1]; }
  const std::set<std::string> allowed={"--scenarios","--controller","--model","--metrics","--telemetry","--id","--sample-every","--infer","--predictions"};
  for(const auto& [key,value]:args) { (void)value; if(!allowed.contains(key)) throw std::runtime_error("Unknown argument: "+key); }
  Forest forest; if(args.contains("--model")) forest.load(args.at("--model"));
  if(args.contains("--infer")) {
   if(forest.empty()) throw std::runtime_error("--infer requires --model");
   std::ifstream in(args.at("--infer")); if(!in) throw std::runtime_error("Cannot read inference CSV"); auto out=output(args.at("--predictions")); out<<"prediction\n";
   std::string line; std::getline(in,line);
   while(std::getline(in,line)) { for(char& c:line) if(c==',') c=' '; std::istringstream row(line); Features f; for(double& x:f) if(!(row>>x)) throw std::runtime_error("Invalid inference row"); out<<forest.predict(f)<<'\n'; }
   return 0;
  }
  if(!args.contains("--scenarios") || !args.contains("--metrics") || !args.contains("--controller")) throw std::runtime_error("Usage: simulator --scenarios FILE --controller baseline|ml|hybrid|teacher --metrics FILE [--model FILE] [--telemetry FILE] [--id ID] [--sample-every N]");
  const auto scenarios=read_scenarios(args.at("--scenarios")); const auto mode=args.at("--controller");
  const int sample=args.contains("--sample-every") ? std::stoi(args.at("--sample-every")):1; if(sample<1) throw std::runtime_error("sample-every must be positive");
  auto metrics=output(args.at("--metrics")); metrics_header(metrics);
  std::ofstream telemetry; if(args.contains("--telemetry")) { telemetry=output(args.at("--telemetry")); telemetry_header(telemetry); }
  int runs=0;
  for(const auto& s:scenarios) {
   if(args.contains("--id") && s.id!=std::stoi(args.at("--id"))) continue;
   int step=0;
   const auto m=simulate(s,Controller(mode,&forest),[&](const Frame& f){ if(telemetry && step%sample==0) write_frame(telemetry,s.id,mode,f); ++step; });
   write_metrics(metrics,m,mode); ++runs;
  }
  if(runs==0) throw std::runtime_error("No matching scenario ID");
  std::cout<<"Evaluated "<<runs<<" scenarios with "<<mode<<'\n';
 } catch(const std::exception& e) { std::cerr<<"Error: "<<e.what()<<'\n'; return 1; }
 return 0;
}