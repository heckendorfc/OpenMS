// --------------------------------------------------------------------------
//                   OpenMS -- Open-Source Mass Spectrometry
// --------------------------------------------------------------------------
// Copyright The OpenMS Team -- Eberhard Karls University Tuebingen,
// ETH Zurich, and Freie Universitaet Berlin 2002-2014.
//
// This software is released under a three-clause BSD license:
//  * Redistributions of source code must retain the above copyright
//    notice, this list of conditions and the following disclaimer.
//  * Redistributions in binary form must reproduce the above copyright
//    notice, this list of conditions and the following disclaimer in the
//    documentation and/or other materials provided with the distribution.
//  * Neither the name of any author or any participating institution
//    may be used to endorse or promote products derived from this software
//    without specific prior written permission.
// For a full list of authors, refer to the file AUTHORS.
// --------------------------------------------------------------------------
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL ANY OF THE AUTHORS OR THE CONTRIBUTING
// INSTITUTIONS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
// EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
// PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
// OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
// WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
// OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
// ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
// --------------------------------------------------------------------------
// $Maintainer: Nico Pfeifer $
// $Authors: $
// --------------------------------------------------------------------------

#include <OpenMS/FORMAT/MascotInfile.h>
#include <OpenMS/CONCEPT/PrecisionWrapper.h>

#include <iostream>
#include <sstream>

using namespace std;

namespace OpenMS
{

  MascotInfile::MascotInfile() :
    ProgressLogger(),
    mz_(0),
    search_title_(""),
    retention_time_(0)
  {
    boundary_ = String::random(22);
    db_ = "MSDB";
    search_type_ = "MIS";
    hits_ = "AUTO";
    cleavage_ = "Trypsin";
    mass_type_ = "Monoisotopic";
    instrument_ = "Default";
    missed_cleavages_ = 1;
    precursor_mass_tolerance_ = 2.0;
    ion_mass_tolerance_ = 1.0;
    taxonomy_ = "All entries";
    form_version_ = "1.01";
    charges_ = "1+, 2+ and 3+";
  }

  void MascotInfile::store(const String& filename,
                           const PeakSpectrum& spec,
                           double mz,
                           double retention_time,
                           String search_title)
  {
    FILE* fp = fopen(filename.c_str(), "wt");

    mz_ = mz;
    retention_time_ = retention_time;
    search_title_ = search_title;

    writeHeader_(fp);
    writeSpectrum_(fp, filename, spec);

    //close file
    fputs("\n", fp);
    fputs("\n--", fp);
    fputs(boundary_.c_str(), fp);
    fputs("--", fp);

    fclose(fp);

  }

  MascotInfile::~MascotInfile()
  {

  }

  void MascotInfile::store(const String& filename,
                           const MSExperiment<>& experiment,
                           String search_title)
  {
    FILE* fp = fopen(filename.c_str(), "wt");

    search_title_ = search_title;

    writeHeader_(fp);
    writeMSExperiment_(fp, filename, experiment);

    //close file
    fputs("\n", fp);
    fputs("\n--", fp);
    fputs(boundary_.c_str(), fp);
    fputs("--", fp);

    fclose(fp);
  }

  void MascotInfile::writeParameterHeader_(const String& name, FILE* fp, bool line_break)
  {
    if (line_break)
    {
      fputs("\n", fp);
    }
    fputs("--", fp);
    fputs(boundary_.c_str(), fp);
    fputs("\nContent-Disposition: form-data; name=\"", fp);
    fputs(name.c_str(), fp);
    fputs("\"\n\n", fp);
  }

  void MascotInfile::writeHeader_(FILE* fp)
  {
    stringstream ss;

    //write header
    //fputs ("MIME-Version: 1.0 (Generated by OpenMS)\nContent-Type: multipart/mixed; boundary=",fp);
    //fputs (boundary_.c_str(),fp);
    //fputs ("\n",fp);

    // search title
    if (search_title_ != "")
    {
      writeParameterHeader_("COM", fp, false);
      fputs(search_title_.c_str(), fp);

      //user name
      writeParameterHeader_("USERNAME", fp);
    }
    else
    {
      //user name
      writeParameterHeader_("USERNAME", fp, false);
    }
    fputs("OpenMS", fp);

    //search type
    writeParameterHeader_("FORMAT", fp);
    fputs("Mascot generic", fp);

    //precursor mass tolerance unit : Da
    writeParameterHeader_("TOLU", fp);
    fputs("Da", fp);

    //ion mass tolerance unit : Da
    writeParameterHeader_("ITOLU", fp);
    fputs("Da", fp);

    //user name
    writeParameterHeader_("FORMVER", fp);
    fputs(form_version_.c_str(), fp);

    //db name
    writeParameterHeader_("DB", fp);
    fputs(db_.c_str(), fp);

    //search type
    writeParameterHeader_("SEARCH", fp);
    fputs(search_type_.c_str(), fp);

    //search type
    writeParameterHeader_("REPORT", fp);
    fputs(hits_.c_str(), fp);

    //cleavage enzyme
    writeParameterHeader_("CLE", fp);
    fputs(cleavage_.c_str(), fp);

    //average/monoisotopic
    writeParameterHeader_("MASS", fp);
    fputs(mass_type_.c_str(), fp);

    //fixed modifications
    for (vector<String>::iterator it = mods_.begin(); it != mods_.end(); ++it)
    {
      writeParameterHeader_("MODS", fp);
      fputs(it->c_str(), fp);
    }

    //variable modifications
    for (vector<String>::iterator it = variable_mods_.begin(); it != variable_mods_.end(); ++it)
    {
      writeParameterHeader_("IT_MODS", fp);
      fputs(it->c_str(), fp);
    }

    //instrument
    writeParameterHeader_("INSTRUMENT", fp);
    fputs(instrument_.c_str(), fp);

    //missed cleavages
    writeParameterHeader_("PFA", fp);
    ss.str("");
    ss << missed_cleavages_;
    fputs(ss.str().c_str(), fp);

    //precursor mass tolerance_
    writeParameterHeader_("TOL", fp);
    ss.str("");
    ss << precursor_mass_tolerance_;
    fputs(ss.str().c_str(), fp);

    //ion mass tolerance_
    writeParameterHeader_("ITOL", fp);
    ss.str("");
    ss << ion_mass_tolerance_;
    fputs(ss.str().c_str(), fp);

    //taxonomy
    writeParameterHeader_("TAXONOMY", fp);
    fputs(taxonomy_.c_str(), fp);

    //charge
    writeParameterHeader_("CHARGE", fp);
    fputs(charges_.c_str(), fp);
  }

  void MascotInfile::writeSpectrum_(FILE* fp,
                                    const String& filename,
                                    const PeakSpectrum& peaks)
  {
    stringstream ss;

    if (mz_ == 0)
    {
      //retention time
      ss.str("");
      ss << precisionWrapper(retention_time_);
      cout << "No precursor m/z information for spectrum with rt: "
           << ss.str() << " present" << "\n";
    }
    else
    {
      //peak data (includes mass and charge)
      fputs("\n--", fp);
      fputs(boundary_.c_str(), fp);
      fputs("\nContent-Disposition: form-data; name=\"FILE\"; filename=\"", fp);
      fputs(filename.c_str(), fp);
      fputs("\"\n\n", fp);

      fputs("BEGIN IONS\n", fp);

      ss.str("");
      ss << precisionWrapper(mz_) << "_" << precisionWrapper(retention_time_);
      fputs(String("TITLE=" + ss.str() + "\n").c_str(), fp);

      //precursor data (includes mz and retention time)
      ss.str("");
      ss << precisionWrapper(mz_);
      fputs(String("PEPMASS=" + ss.str() + "\n").c_str(), fp);

      //retention time
      ss.str("");
      ss << precisionWrapper(retention_time_);
      fputs(String("RTINSECONDS=" + ss.str() + "\n").c_str(), fp);

      for (PeakSpectrum::const_iterator it = peaks.begin(); it != peaks.end(); ++it)
      {
        //mass
        ss.str("");
        ss << precisionWrapper(it->getMZ());
        fputs(ss.str().c_str(), fp);
        fputs(" ", fp);
        //intensity
        ss.str("");
        ss << precisionWrapper(it->getIntensity());
        fputs(ss.str().c_str(), fp);
        fputs("\n", fp);
      }
      fputs("END IONS\n", fp);
    }
  }

  void MascotInfile::writeMSExperiment_(FILE* fp,
                                        const String& filename,
                                        const MSExperiment<>& experiment)
  {
    String temp_string;
    stringstream ss;

    fputs("\n--", fp);
    fputs(boundary_.c_str(), fp);
    fputs("\nContent-Disposition: form-data; name=\"FILE\"; filename=\"", fp);
    fputs(filename.c_str(), fp);
    fputs("\"\n\n", fp);

    for (Size i = 0; i < experiment.size(); i++)
    {
      MSSpectrum<> peaks = experiment[i];
      peaks.sortByPosition();
      Precursor precursor_peak;
      if (experiment[i].getPrecursors().size() > 0)
      {
        precursor_peak = experiment[i].getPrecursors()[0];
      }
      if (experiment[i].getPrecursors().size() > 1)
      {
        std::cerr << "Warning: The spectrum written to the Mascot file '" << filename << "' has more than one precursor. The first precursor is used!" << "\n";
      }

      if (experiment[i].getMSLevel() == 0)
      {
        cout << "MascotInfile: MSLevel is set to 0, ignoring this spectrum!" << "\n";
      }

      if (experiment[i].getMSLevel() == 2)
      {
        if (precursor_peak.getMZ() == 0)
        {
          cerr << "Warning: No precursor m/z information for spectrum with rt: " << precisionWrapper(experiment[i].getRT()) << " present" << "\n";
        }
        else
        {
          fputs("\nBEGIN IONS\n", fp);

          ss.str("");
          ss << precisionWrapper(precursor_peak.getMZ()) << "_" << precisionWrapper(experiment[i].getRT());
          fputs(String("TITLE=" + ss.str() + "\n").c_str(), fp);

          //precursor data (includes mz and retention time)
          ss.str("");
          ss << precisionWrapper(precursor_peak.getMZ());
          fputs(String("PEPMASS=" + ss.str() + "\n").c_str(), fp);

          //retention time
          ss.str("");
          ss << precisionWrapper(experiment[i].getRT());
          fputs(String("RTINSECONDS=" + ss.str() + "\n").c_str(), fp);

          if (precursor_peak.getCharge() != 0)
          {
            ss.str("");
            if (precursor_peak.getCharge() > 0)
            {
              ss << "+";
            }
            else
            {
              ss << "-";
            }
            ss << precursor_peak.getCharge();
            fputs(String("CHARGE=" + ss.str() + "\n").c_str(), fp);
          }
          fputs("\n", fp);

          for (PeakSpectrum::iterator it = peaks.begin();
               it != peaks.end();
               ++it)
          {
            //mass
            ss.str("");
            ss << precisionWrapper(it->getMZ());
            fputs(ss.str().c_str(), fp);
            fputs(" ", fp);
            //intensity
            ss.str("");
            ss << precisionWrapper(it->getIntensity());
            fputs(ss.str().c_str(), fp);
            fputs("\n", fp);
          }
          fputs("END IONS\n", fp);
        }
      }
    }
  }

  const String& MascotInfile::getBoundary()
  {
    return boundary_;
  }

  void MascotInfile::setBoundary(const String& boundary)
  {
    boundary_ = boundary;
  }

  const String& MascotInfile::getDB()
  {
    return db_;
  }

  void MascotInfile::setDB(const String& db)
  {
    db_ = db;
  }

  const String& MascotInfile::getSearchType()
  {
    return search_type_;
  }

  void MascotInfile::setSearchType(const String& search_type)
  {
    search_type_ = search_type;
  }

  const String& MascotInfile::getHits()
  {
    return hits_;
  }

  void MascotInfile::setHits(const String& hits)
  {
    hits_ = hits;
  }

  const String& MascotInfile::getCleavage()
  {
    return cleavage_;
  }

  void MascotInfile::setCleavage(const String& cleavage)
  {
    cleavage_ = cleavage;
  }

  const String& MascotInfile::getMassType()
  {
    return mass_type_;
  }

  void MascotInfile::setMassType(const String& mass_type)
  {
    mass_type_ = mass_type;
  }

  const std::vector<String>& MascotInfile::getModifications()
  {
    return mods_;
  }

  void MascotInfile::setModifications(const std::vector<String>& mods)
  {
    mods_ = mods;
  }

  const std::vector<String>& MascotInfile::getVariableModifications()
  {
    return variable_mods_;
  }

  void MascotInfile::setVariableModifications(const std::vector<String>& variable_mods)
  {
    variable_mods_ = variable_mods;
  }

  const String& MascotInfile::getInstrument()
  {
    return instrument_;
  }

  void MascotInfile::setInstrument(const String& instrument)
  {
    instrument_ = instrument;
  }

  UInt MascotInfile::getMissedCleavages()
  {
    return missed_cleavages_;
  }

  void MascotInfile::setMissedCleavages(UInt missed_cleavages)
  {
    missed_cleavages_ = missed_cleavages;
  }

  float MascotInfile::getPrecursorMassTolerance()
  {
    return precursor_mass_tolerance_;
  }

  void MascotInfile::setPrecursorMassTolerance(float precursor_mass_tolerance)
  {
    precursor_mass_tolerance_ = precursor_mass_tolerance;
  }

  float MascotInfile::getPeakMassTolerance()
  {
    return ion_mass_tolerance_;
  }

  void MascotInfile::setPeakMassTolerance(float ion_mass_tolerance)
  {
    ion_mass_tolerance_ = ion_mass_tolerance;
  }

  const String& MascotInfile::getTaxonomy()
  {
    return taxonomy_;
  }

  void MascotInfile::setTaxonomy(const String& taxonomy)
  {
    taxonomy_ = taxonomy;
  }

  const String& MascotInfile::getFormVersion()
  {
    return form_version_;
  }

  void MascotInfile::setFormVersion(const String& form_version)
  {
    form_version_ = form_version;
  }

  const String& MascotInfile::getCharges()
  {
    return charges_;
  }

  void MascotInfile::setCharges(std::vector<Int>& charges)
  {
    stringstream ss;

    sort(charges.begin(), charges.end());

    for (Size i = 0; i < charges.size(); i++)
    {
      if (i == 0)
      {
        if (charges[i] > 0)
        {
          ss << charges[i] << "+";
        }
        else
        {
          ss << (-1 * charges[i]) << "-";
        }
      }
      else if (i < (charges.size() - 1))
      {
        if (charges[i] > 0)
        {
          ss << ", " << charges[i] << "+";
        }
        else
        {
          ss << ", " << (-1 * charges[i]) << "-";
        }
      }
      else
      {
        if (charges[i] > 0)
        {
          ss << " and " << charges[i] << "+";
        }
        else
        {
          ss << " and " << (-1 * charges[i]) << "-";
        }
      }
    }
    charges_ = ss.str();
  }

  bool MascotInfile::getNextSpectrum_(istream& is, vector<pair<double, double> >& spectrum, UInt& charge, double& precursor_mz, double& precursor_int, double& rt, String& title)
  {
    bool ok(false);
    spectrum.clear();
    charge = 0;
    precursor_mz = 0;
    precursor_int = 0;

    String line;
    // seek to next peak list block
    while (getline(is, line, '\n'))
    {
      // found peak list block?
      if (line.trim() == "BEGIN IONS")
      {
        ok = false;
        while (getline(is, line, '\n'))
        {
          // parse precursor position
          if (line.trim().hasPrefix("PEPMASS"))
          {
            String tmp = line.substr(8);
            tmp.substitute('\t', ' ');
            vector<String> split;
            tmp.split(' ', split);
            if (split.size() == 1)
            {
              precursor_mz = split[0].trim().toDouble();
            }
            else
            {
              if (split.size() == 2)
              {
                precursor_mz = split[0].trim().toDouble();
                precursor_int = split[1].trim().toDouble();
              }
              else
              {
                throw Exception::ParseError(__FILE__, __LINE__, __PRETTY_FUNCTION__, "cannot parse PEPMASS: " + line, "");
              }
            }
          }
          if (line.trim().hasPrefix("CHARGE"))
          {
            String tmp = line.substr(7);
            tmp.remove('+');
            charge = tmp.toInt();
          }
          if (line.trim().hasPrefix("RTINSECONDS"))
          {
            String tmp = line.substr(12);
            rt = tmp.toDouble();
          }
          if (line.trim().hasPrefix("TITLE"))
          {
            // test if we have a line like "TITLE= Cmpd 1, +MSn(595.3), 10.9 min"
            if (line.hasSubstring("min"))
            {
              try
              {
                vector<String> split;
                line.split(',', split);
                if (!split.empty())
                {
                  for (Size i = 0; i != split.size(); ++i)
                  {
                    if (split[i].hasSubstring("min"))
                    {
                      vector<String> split2;
                      split[i].trim().split(' ', split2);
                      if (!split2.empty())
                      {
                        rt = split2[0].trim().toDouble() * 60.0;
                      }
                    }
                  }
                }
              }
              catch (Exception::BaseException& /*e*/)
              {
                // just do nothing and write the whole title to spec
                vector<String> split;
                line.split('=', split);
                if (split.size() >= 2)
                {
                  title = split[1];
                }
              }
            }
            else // just write the title as metainfo to the spectrum
            {
              vector<String> split;
              line.split('=', split);
              if (split.size() >= 2)
              {
                title = split[1];
              }
              // TODO concatenate the other parts if the title contains additional '=' chars
            }
          }
          if (line.trim().size() > 0 && isdigit(line[0]))
          {
            do
            {
              line.substitute('\t', ' ');
              vector<String> split;
              line.split(' ', split);
              if (split.size() == 2)
              {
                spectrum.push_back(make_pair(split[0].toDouble(), split[1].toDouble()));
              }
              else
              {
                if (split.size() == 3)
                {
                  spectrum.push_back(make_pair(split[0].toDouble(), split[1].toDouble()));
                  // @improvement add meta info e.g. charge, name... (Andreas)
                }
                else
                {
                  throw Exception::ParseError(__FILE__, __LINE__, __PRETTY_FUNCTION__, "the line (" + line + ") should contain m/z and intensity value separated by whitespace!", "");
                }
              }
            }
            while (getline(is, line, '\n') && line.trim() != "END IONS");
            if (line.trim() == "END IONS")
            {
              // found spectrum
              return true;
            }
            else
            {
              throw Exception::ParseError(__FILE__, __LINE__, __PRETTY_FUNCTION__, "Found \"BEGIN IONS\" but not the corresponding \"END IONS\"!", "");
            }
          }
        }
      }
    }

    return ok;
  }

} // namespace OpenMS
