// SKYFORGE: an explicitly modeled body-drag disturbance, not CFD/aeroacoustics.
#include <cmath>
#include <chrono>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/transport/Node.hh>
#include <gz/msgs/vector3d.pb.h>

class SkyforgeWind : public gz::sim::System,
                     public gz::sim::ISystemConfigure,
                     public gz::sim::ISystemPreUpdate {
  std::string modelName{"x3"};
  double cdArea{0.045}, rho{1.225}, lastPublish{-1.0};
  bool constantWind{false}, publishWind{true};
  double windX{0.7},windY{0.25};
  gz::sim::Link link;
  gz::transport::Node node;
  gz::transport::Node::Publisher pub;
 public:
  void Configure(const gz::sim::Entity &, const std::shared_ptr<const sdf::Element> &sdf,
                 gz::sim::EntityComponentManager &, gz::sim::EventManager &) override {
    if (sdf->HasElement("model_name")) modelName=sdf->Get<std::string>("model_name");
    if (sdf->HasElement("cd_area")) cdArea=sdf->Get<double>("cd_area");
    if (sdf->HasElement("constant_wind")) constantWind=sdf->Get<bool>("constant_wind");
    if (sdf->HasElement("wind_x")) windX=sdf->Get<double>("wind_x");
    if (sdf->HasElement("wind_y")) windY=sdf->Get<double>("wind_y");
    if (sdf->HasElement("publish_wind")) publishWind=sdf->Get<bool>("publish_wind");
    pub=node.Advertise<gz::msgs::Vector3d>("/skyforge/wind");
  }
  void PreUpdate(const gz::sim::UpdateInfo &info,
                 gz::sim::EntityComponentManager &ecm) override {
    if (info.paused) return;
    if (!link.Valid(ecm)) {
      auto modelEntity=ecm.EntityByComponents(gz::sim::components::Name(modelName),
                                             gz::sim::components::Model());
      if (modelEntity==gz::sim::kNullEntity) return;
      link=gz::sim::Link(gz::sim::Model(modelEntity).CanonicalLink(ecm));
      link.EnableVelocityChecks(ecm,true);
      return;
    }
    auto velocity=link.WorldLinearVelocity(ecm);
    if (!velocity) return;
    double t=std::chrono::duration<double>(info.simTime).count();
    // Smooth bounded deterministic gusts; change of prevailing wind after 45 s.
    double transition=0.5*(1.0+std::tanh((t-45.0)/3.0));
    gz::math::Vector3d wind(0.7-1.0*transition+0.25*std::sin(t*0.31),
                           0.25+0.2*std::sin(t*0.19),0.0);
    if (constantWind) wind.Set(windX,windY,0.0);
    auto relative=*velocity-wind;
    auto force=-0.5*rho*cdArea*relative.Length()*relative;
    link.AddWorldForce(ecm,force);
    if (publishWind && t-lastPublish>=0.05) {
      gz::msgs::Vector3d msg;
      msg.set_x(wind.X());msg.set_y(wind.Y());msg.set_z(wind.Z());
      pub.Publish(msg);lastPublish=t;
    }
  }
};
GZ_ADD_PLUGIN(SkyforgeWind,gz::sim::System,
              gz::sim::ISystemConfigure,gz::sim::ISystemPreUpdate)
GZ_ADD_PLUGIN_ALIAS(SkyforgeWind,"SkyforgeWind")
