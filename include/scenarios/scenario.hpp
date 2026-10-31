#pragma once
#include "simulation/types.hpp"
#include <filesystem>
namespace driving { std::vector<Scenario> read_scenarios(const std::filesystem::path& path); }